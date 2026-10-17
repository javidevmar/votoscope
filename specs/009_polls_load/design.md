# Diseño — `polls_load`

Feature 9. Plan de iniciativa: [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), §§ «Obtención (bronce)» (`ingest-polls [ruta]`), «Carga (bronce → plata)» y decisión 4 (pase de resolución). Consume el adaptador de la feature 8 (`parse_polls`, `PollRow`, `ELECTION_TYPE`, `PARTY_COLUMNS`) sobre los snapshots que deja la feature 6 en `data/raw/polls/`, y los carga en `silver`. No descarga (6), no parsea wikitexto (7–8) y no programa el job (10).

**No toca el modelo de datos**: `pollster`, `poll` y `poll_result` existen desde la feature 5; sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica). Sin dependencias nuevas (`sqlalchemy` ya está). Sin excepciones nuevas: se reutiliza `IngestError`. Se reutilizan `sha256` y `slugify` de `elections/loaders/election.py`, `SOURCE` de `polls/fetch.py` y `ELECTION_TYPE`/`PARTY_COLUMNS`/`parse_polls` de `polls/adapters/wikipedia_polls.py`.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/loaders/polls.py` — loader de snapshots (bronce + plata) y pase de resolución |
| modificar | `ingestor/src/ingestor/cli.py` — subcomando `ingest-polls` con `[ruta]` y `--force` |
| crear | `ingestor/tests/conftest.py` — fixtures de BD (esquemas Postgres aislados; ver «Tests») |
| crear | `ingestor/tests/test_polls_load.py` — tests (R1–R30) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/load_small.wikitext` — snapshot sintético (revid «nuevo») |
| crear | `ingestor/tests/fixtures/wikipedia_polls/load_other.wikitext` — snapshot sintético (revid «viejo» y reemplazo) |
| modificar | `docs/ingestor/ingesta.md` — comando `ingest-polls` y su comportamiento (R29) |
| modificar | `ingestor/AGENTS.md` — comando y bullet de `polls/` (R30) |

## Firmas nuevas — `src/ingestor/polls/loaders/polls.py`

```python
@dataclass(frozen=True)
class PollsOutcome:
    file: Path
    status: str  # processed | skipped | failed
    revision_id: int


def ingest_polls_path(
    session_factory: sessionmaker,
    path: Path,
    raw_dir: Path,
    force: bool = False,
) -> list[PollsOutcome]: ...


def ingest_snapshot(
    session_factory: sessionmaker,
    path: Path,
    raw_dir: Path,
    force: bool = False,
) -> PollsOutcome: ...


def load_polls(session: Session, rows: list[PollRow], revision_id: int) -> None: ...


def resolve_poll_elections(session_factory: sessionmaker) -> int: ...
```

Internos: `_snapshot_files(path)`, `_revision_id(path)`, `_validate(rows, revision_id)`, `_resolve_pollsters(session, rows)`, `_resolve_parties(session, rows)`, `_pct_sum_warning(...)`.

Detalles que fijan el contrato:

- La firma de `ingest_polls_path` es la del loader de elecciones (`ingest_path(session_factory, path, raw_dir, force)`): la factoría de sesiones se inyecta (los tests pasan la suya; el CLI, `SessionLocal`).
- `PollsOutcome.status` usa los tres estados del loader de elecciones; el guard de revisión produce `skipped` **con warning** (la distinción vive en el log, no en el estado).
- `resolve_poll_elections` devuelve cuántos sondeos enlazó (0 si no había nada que enlazar) y se llama desde `ingest_polls_path`; los tests también la llaman directamente.

## Flujo de `ingest_polls_path`

1. `resolve_poll_elections(session_factory)` — **siempre, al inicio**: el pase no queda detrás del guard «sin novedades» (decisión 4 del plan). Si `path` no existe se ha lanzado `IngestError` antes de llegar aquí (ver paso 2).
2. `_snapshot_files(path)`:
   - ruta inexistente → `IngestError` (R26);
   - fichero → `[path]`; directorio → `sorted(path.rglob("*.wikitext"))` (sin error si queda vacío: no hay pendientes, R24);
   - cada fichero debe estar bajo `raw_dir` (`Path.resolve().is_relative_to(raw_root)`) → si no, `IngestError` (R27);
   - se ordenan por `revision_id` ascendente (procesar 100 antes que 101 evita que el guard marque 100 como «anterior» tras cargar 101).
3. Por cada fichero: `ingest_snapshot(...)` dentro de `try/except IngestError`; un fallo registra el error por log, añade el outcome `failed` y **no aborta** los demás ficheros (mismo patrón que `ingest_path`).
4. Devuelve los outcomes (el CLI resume y decide el exit code, R25).

## `ingest_snapshot` — guard y registro

1. `revid = _revision_id(path)`: `path.suffix == ".wikitext"` y `path.stem.isdigit()`, si no `IngestError` (R28).
2. `digest = sha256(path)` (reutilizado de `elections/loaders/election.py`).
3. Consulta del registro por sha256: si la fila existe y está `processed` y no hay `--force` → log INFO y outcome `skipped` (R9).
4. Guard de revisión: `max_rev = max(poll.revision_id)` (una consulta); si `max_rev is not None and revid < max_rev and not force` → `logger.warning("snapshot revision %s is older than the loaded revision %s; ignored (use --force)", revid, max_rev)` y outcome `skipped` **sin registrar** (R10).
5. Si el sha no está en bronce, inserta `Ingestion(file_path=str(path.resolve().relative_to(raw_root)), sha256=digest, size_bytes=path.stat().st_size, source=SOURCE, status="registered")` y hace commit (R1).
6. `rows = parse_polls(path.read_text(encoding="utf-8"))`.
7. Transacción de plata: `with session_factory() as session: load_polls(session, rows, revid); session.commit()`. Si algo falla: marca `failed` (update por sha, transacción aparte) y re-lanza (R22).
8. Marca `processed` (update por sha) y devuelve `processed` (R8).

El registro en bronce y los cambios de estado van en transacciones aparte, como en `elections/loaders/election.py`; la transacción única es la de plata (R2).

## `load_polls` — get-or-create, borrado e inserción

1. `_validate(rows, revision_id)` (tabla de validaciones abajo). Validar antes de tocar nada: un fallo no escribe ni borra.
2. `_resolve_pollsters`: slugs `slugify(row.pollster_name)`; `select(Pollster).where(slug.in_(...))` + creación de los que falten; `flush` (R3).
3. `_resolve_parties`: claves de `row.results`; para los slugs del mapeo, nombres `{col.slug: col.name for col in PARTY_COLUMNS.values()}`; para rótulos crudos (R31): slug = `slugify(clave)`, nombre = clave y `logger.warning` de alta; los que falten se crean (`names.get(slug, slug)` defensivo); `flush` (R4, R31).
4. Borrado total: `session.execute(delete(PollResult))` y `session.execute(delete(Poll))` — `pollster` y `party` no se tocan (R7).
5. Inserción en bloque: `insert(Poll).returning(Poll.id)` con una fila por `PollRow` (`election_type=ELECTION_TYPE`, `election_id=None`, `revision_id=revid`; R5) y `insert(PollResult)` con una fila por resultado, casando `poll_id` por orden de retorno (R6).
6. Warnings de suma de porcentajes, por sondeo (R20).

Con las fixtures (3 filas) cualquier estrategia vale; con la página real son ~584 sondeos y ~8,7k resultados, así que la inserción va en bloque (`insert()` con `returning`), no con objetos ORM.

## Validaciones (R17–R21)

| Condición | Efecto | Subcadena estable del mensaje | R |
| --- | --- | --- | --- |
| `not row.source.strip() or not row.pollster_name.strip()` | `IngestError` (rollback) | `no signature` | R17 |
| `len(row.results) < 2` | `IngestError` (rollback) | `fewer than two parties` | R18 |
| `pct` fuera de 0–100; `seats_min`/`seats_max` fuera de 0–350; `seats_min > seats_max` | `IngestError` (rollback) | `out of range` | R19 |
| `sum(pct) > 100.5` (constante `PCT_SUM_LIMIT`) | warning y seguir | `percentages add up to` | R20 |
| `not rows` | `IngestError` (rollback) | `no polls` | R21 |

- `MAX_SEATS = 350` (tamaño del Congreso): la proyección de escaños de un sondeo al Congreso no puede superarlo.
- El rango de `pct` y `turnout` también existe como CHECK en la base (`poll_result_pct_range`, `poll_turnout_range`); la validación del loader da el mensaje antes del commit, el CHECK es la red de seguridad.
- La suma es warning por decisión del plan: la página no publica «otros»/indecisos, así que los % no suman 100.

## Pase de resolución — `resolve_poll_elections`

- Carga los sondeos con `election_id` nulo (R16) y, por tipo, las elecciones de ese tipo con ámbito nacional (`autonomous_community_ine_code IS NULL AND municipality_id IS NULL`) ordenadas por fecha (una consulta por tipo, cacheada en un dict — no N+1).
- Para cada sondeo con `fieldwork_end`: la primera elección con `date > fieldwork_end` (R12); sin candidata queda nulo (R13); sin `fieldwork_end` no se toca (R14).
- Solo escribe si enlazó algo (`commit`); log INFO `linked %d polls to elections` cuando `linked > 0` (R15).
- Idempotente por construcción: solo mira `election_id IS NULL` (R16).

## CLI — `src/ingestor/cli.py`

- Nuevo subparser:

```python
polls = subparsers.add_parser(
    "ingest-polls",
    help="ingest polls snapshots into silver (skips processed; --force reloads)",
)
polls.add_argument("path", type=Path, nargs="?", default=None,
                   help="snapshot file or directory (default: RAW_DIR/polls)")
polls.add_argument("--force", action="store_true",
                   help="reload snapshots even if processed or older than the loaded revision")
```

- Handler dentro del `try` existente, con su propio resumen (el `PollsOutcome` no tiene `directory` como el de elecciones):

```python
if args.command == "ingest-polls":
    outcomes = ingest_polls_path(
        SessionLocal,
        args.path or settings.raw_dir / "polls",
        settings.raw_dir,
        force=args.force,
    )
    for outcome in outcomes:
        logger.info("%s: %s", outcome.file, outcome.status)
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0
```

- `IngestError` → log ERROR y exit 1 (vía el `except` existente); «sin novedades» y guard → exit 0 (R25). El comando no descarga ni llama a la API.

## Fixtures

| Fixture | Contenido | Fija |
| --- | --- | --- |
| `load_small.wikitext` | `====Voting intention estimates====` + `=====2026=====`, tabla mínima con las cuatro fijas, `PP`/`PSOE`/`SALF` y `Lead`; filas `Alpha/Medio` (`1–2 Oct`, `1,000`, `67.6`, PP `32.6`+`141`, PSOE `30.1`+`110`, SALF `3.2`+`0`) y `CIS (Target Point)` (`?`, PP `31.0`+`135/137`, PSOE `29.5`+`112`, SALF `2.9`+`?`) | firma con `/` y `(`, fechas, muestra/participación, resultados, creación de `salf` |
| `load_other.wikitext` | misma estructura, columnas `PSOE`/`PP` y una fila `Beta/Medio` (`5–6 Sep`, `2,000`, `70`, PSOE `28.4`+`104`, PP `33.1`+`145`) | contenido distinto para guard/reemplazo |

Las celdas van **una por línea** (`!`/`|`), como la fuente real: el lexer de la feature 7 no soporta `||`/`!!`. Las validaciones (R17–R21) van como cadenas inline en el test, no necesitan fixture.

## Tests — `ingestor/tests/`

### `conftest.py` — fixture de BD (infra nueva)

El loader necesita una base de datos real (transacción, CHECK, FK, `NUMERIC`). Estrategia verificada contra el Postgres local:

- `engine = create_engine(settings.database_url, execution_options={"schema_translate_map": {"bronze": "polls_test_bronze", "silver": "polls_test_silver"}})` — el loader escribe en esquemas de test aislados, nunca en los de la aplicación.
- Fixture de sesión `polls_session_factory`: `DROP SCHEMA IF EXISTS … CASCADE` + `CREATE SCHEMA` de ambos, `Base.metadata.create_all(engine)`; si la conexión falla (`OperationalError`) → `pytest.skip("Postgres is not reachable…")` (la CI lo levanta como servicio; `init.sh` no exige BD); al terminar, `DROP SCHEMA … CASCADE`.
- Fixture de test `db` (o `clean_session_factory`): vacía todas las tablas (`reversed(Base.metadata.sorted_tables)` → `table.delete()`) antes de cada test y devuelve la factoría.

### `test_polls_load.py`

Helper `_snapshot(tmp_path, revid, fixture)`: copia la fixture a `tmp_path/polls/wikipedia-en/2026-general/{revid}.wikitext`. Los tests de CLI parchean `ingestor.cli.SessionLocal` a la factoría de test y `settings.raw_dir` a `tmp_path`.

| Test previsto | Cubre |
| --- | --- |
| `test_cli_registers_and_loads` (sha256, `source`, ruta relativa, `processed`; pollster `Alpha`/`CIS`; `poll` con `revision_id` 200, fechas, muestra, turnout; `poll_result` con pct/escaños; `party` `salf` creado con «Se Acabó La Fiesta») | R1, R3, R4, R5, R6, R7, R8, R23, R25 |
| `test_existing_party_and_pollster_reused` (pre-insertados: mismo id, sin duplicados) | R3, R4 |
| `test_unknown_label_creates_party_with_warning` (snapshot inline con columna `FA`: `fa` creado con nombre «FA» + warning; segunda carga lo reutiliza) | R31 |
| `test_replacement_deletes_previous_polls` (carga 200 y luego 300; `poll`/`poll_result` solo del último; pollster viejo conservado) | R7 |
| `test_skip_processed` (segunda ejecución: `skipped`, sin escrituras, exit 0) | R9, R25 |
| `test_guard_ignores_older_revision` (200 cargado + 100 en disco: warning «older than», `skipped`, silver intacto, 100 sin fila en bronce, exit 0) | R10, R25 |
| `test_force_reloads_processed_and_older` (`--force`: 100 cargado, silver retrocede) | R11 |
| `test_resolution_links_after_fieldwork` (sondeos insertados a mano: enlaza a la primera elección nacional posterior; ignora otra CCAA/municipio y otro tipo) | R12 |
| `test_resolution_leaves_unmatched_and_null_fieldwork` (sin elección posterior → nulo; sin `fieldwork_end` → nulo) | R13, R14 |
| `test_resolution_runs_without_pending_snapshots` (`ingest_polls_path` sobre directorio sin snapshots: enlaza igual; exit 0) | R15, R24 |
| `test_resolution_is_idempotent` (segunda pasada: 0 enlaces, sin cambios) | R16 |
| `test_missing_signature_fails` (celda de firma vacía → `IngestError`/`failed`, silver intacto) | R17, R22 |
| `test_fewer_than_two_parties_fails` (solo un partido con valor) | R18, R22 |
| `test_pct_and_seats_out_of_range_fail` (`150` de pct; `400` de escaños) | R19, R22 |
| `test_pct_sum_warns_and_loads` (60 + 45: warning «add up to», carga en verde) | R20 |
| `test_empty_snapshot_fails_and_keeps_silver` (snapshot sin sondeos tras una carga buena: `failed` y datos anteriores intactos) | R21, R22 |
| `test_missing_path_raises` | R26 |
| `test_snapshot_outside_raw_dir_raises` | R27 |
| `test_bad_snapshot_filename_raises` (`notarevid.wikitext`) | R28 |
| `test_cli_exit_codes` (fallo → 1; sin novedades → 0) | R25 |
| `test_docs_ingesta` (subcadenas `ingest-polls`, `wikipedia-en`, `revision_id`, `failed`) | R29 |
| `test_docs_ingestor_agents` (subcadenas `ingest-polls`, `polls.py`) | R30 |

## Documentación (texto pretendido)

- `docs/ingestor/ingesta.md` (R29): sección `### ingestor ingest-polls [ruta] [--force]` bajo «Comandos» (ruta por defecto `RAW_DIR/polls/` recursivo; fichero o directorio; registro en bronce con sha256 y `source = wikipedia-en`; reemplazo total de `poll`/`poll_result`; guard por `revision_id` y `--force`; pase de resolución de elección en cada ejecución; validaciones y warning de suma > 100.5; fallo → rollback y `failed`), una sección «Comportamiento de `ingest-polls`» con el flujo numerado y las filas de `pollster`/`poll`/`poll_result` en la tabla «Qué queda en `silver`».
- `ingestor/AGENTS.md` (R30): bullet de `src/ingestor/polls/` con `loaders/polls.py`; comando `uv run ingestor ingest-polls [ruta]` en «Comandos»; mención en «Ingesta (bronce → plata)».
- Los tests de docs comprueban subcadenas estables, no el texto completo.

## Decisiones

- **El pase de resolución corre al inicio de cada ejecución** (antes de seleccionar pendientes): es la lectura de la decisión 4 del plan («corre en cada ejecución, también sin snapshot nuevo») y de la instrucción de la cadena («antes del guard "sin novedades"»). Consecuencia documentada: un snapshot cargado en esa misma ejecución queda enlazado en la siguiente (≤12 h con el job de la feature 10); la alternativa de correrlo también tras la carga se descarta por YAGNI.
- **Guard sin registrar**: un snapshot ignorado por el guard no se añade a `bronze.ingestion` (bronce = ficheros ingeridos; registrar `processed` mentiría). Se re-avisa con warning en cada ejecución; `--force` lo reprocesa.
- **Reemplazo total, no por revisión**: decisión 3 del plan; `silver` refleja el último snapshot y el histórico vive en bronce. Consecuencia: los ids de `poll` cambian en cada recarga (inocuo, ya previsto en el plan).
- **Validar antes de borrar**: las validaciones estructurales van al principio de `load_polls`; un fallo no llega a tocar `silver` (el rollback es trivial) y el mensaje del `IngestError` nombra la revisión y la fila.
- **Snapshot vacío = error** (R21, extra sobre el acceptance): un parseo vacío por deriva del formato haría un borrado total sin inserción; abortar deja `silver` como estaba y el fichero `failed`.
- **Inserción en bloque con `returning`**: ~9k filas por ejecución; los objetos ORM se descartan. El orden de ids devuelto por `insert().returning()` con `insertmanyvalues` sigue al de entrada (Postgres).
- **Tests con Postgres en esquemas aislados** (`schema_translate_map`): fidelidad total (CHECK, FK, `NUMERIC`) sin tocar los esquemas reales ni crear bases nuevas; `skip` si no hay Postgres para no romper `init.sh` sin Docker (la CI lo levanta como servicio).
- **`SOURCE` se importa de `polls/fetch.py`**: una sola definición del nombre de la fuente para descarga y registro.
- **Sin logs INFO por celda**: los parsers/adaptadores del repo solo avisan; el loader sí registra el resultado por fichero (procesado/saltado) y los enlaces del pase.

## Alternativas descartadas

1. **SQLite en memoria para los tests**: `silver.election` no se puede crear (CHECK `num_nonnulls` es de Postgres; verificado con `create_all`), y un loader de hechos merece CHECK/FK/`NUMERIC` reales; además el coste es una fixture de `conftest.py`, no código de producción.
2. **Tests contra los esquemas reales de la BD local**: el reemplazo total borra `poll`/`poll_result` de verdad (destruiría los datos de la feature 11); los esquemas traducidos aíslan sin `CREATE DATABASE`.
3. **Resolver la elección dentro de `load_polls`** (solo al cargar): no correría «también sin snapshot nuevo» (decisión 4 del plan).
4. **Registrar como `processed` los snapshots ignorados por el guard**: mentiría en bronce y silenciaría el aviso; el plan dice «se ignora con warning».
5. **Validar la suma de porcentajes como error**: el plan la fija como warning (la página no publica «otros»).
6. **Una consulta de elecciones por sondeo**: N+1 (~584 sondeos); se cachean por tipo.
7. **Resolver por fecha de fichero (`mtime`) u orden de directorio**: el contrato es el `revision_id` del nombre (feature 6); el nombre manda.
8. **`--page`/`--source` en `ingest-polls`**: el comando lee ficheros, no páginas; `--page` es de `fetch-polls` (feature 6).

## Interfaz para las features 10–11

- Feature 10 (job 2×/día): el ciclo «sin novedades» es `fetch-polls` (una llamada a la API) + `ingest-polls` (todo `processed` → sin escrituras, exit 0, con el pase de resolución corriendo igual).
- Feature 11 (ejecución real): `uv run ingestor fetch-polls && uv run ingestor ingest-polls` sobre el Postgres local; el cotejo manual usa `poll.source`/`revision_id`.
