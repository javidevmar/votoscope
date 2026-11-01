# Diseño — `party_reload`

Feature 13 de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`), redactada absorbiendo el diseño de la iniciativa. Depende de la feature 12 ([`specs/012_party_catalog/`](../012_party_catalog/)): el catálogo `ingestor/src/ingestor/data/party_catalog.toml` y el módulo `ingestor/src/ingestor/parties.py` (`normalize`, `slugify`, `Catalog`, `load_catalog`, `PartyResolver`; interfaz exacta en su §«Firmas nuevas» y §«Interfaz para las features 13 y 14»).

Alcance: (a) `_resolve_parties` del loader de elecciones resuelve con `PartyResolver` (sin slug provisional), (b) recarga real `--force` de los 13 procesos locales con las comprobaciones de identidad y la limpieza de huérfanos, y (c) actualización de los tres documentos que describen la identidad de `party`. El adaptador y el loader de sondeos llegan en la feature 14.

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica); `party` y `party_election` valen tal cual y `silver` se recalcula reingiriendo el bronce. Sin dependencias nuevas. Sin excepciones nuevas (`IngestError`, ya usada por `load_catalog`). Sin CLI. Sin firmas públicas nuevas.

## Estado observado al redactar (2026-10-18, local; no congelado)

- `data/raw/congreso/` tiene los 13 procesos (`02198606`, `02198910`, `02199306`, `02199603`, `02200003`, `02200403`, `02200803`, `02201111`, `02201512`, `02201606`, `02201904`, `02201911`, `02202307`); `silver` ya tiene las 13 elecciones `congress` nacionales con sus hechos.
- `silver.party`: 549 filas; **27 grupos** por puntuación; las 7 marcas del acceptance repartidas en 14 filas (`pp`, `psoe`, `bng`+`b-n-g`, `upl`+`u-p-l`, `iu`+`i-u`, `c-s`+`cs`, `fia`+`f-i-a`, `p-p`, `p-s-o-e`).
- Sondeos ya cargados (575 `poll`): hay filas `party` referenciadas solo por `poll_result` (p. ej. `salf`); la limpieza de huérfanos DEBE preservarlas.
- Huérfanos hoy: 0. Aparecen **al fusionar la recarga**: las filas viejas pierden sus candidaturas y quedan sin `party_election` (y sin `poll_result`), esperando el `DELETE` de mantenimiento.
- Avisos esperados en la recarga: pocos o ninguno. Toda etiqueta ya tiene una fila con ese mismo `name` literal (la identidad era el slug de la misma sigla), así que casa por nombre (paso 2 del resolver) o por ficha; el warning solo aparecerá para etiquetas nunca vistas.

## Decisión

- **El loader delega la identidad**: `_resolve_parties` construye un `PartyResolver` con las filas `Party` existentes y el catálogo (`load_catalog()`) y resuelve cada cabecera nacional con la precedencia de `parties.py` (catálogo → nombre existente → alta con warning). Desaparece el slug provisional (`slugify(short_name)` + colisión por código calculada a mano).
- **Sin cambio de esquema ni de contrato de datos**: `party_election` sigue escribiéndose igual (código, `short_name`, `name`); lo único que cambia es a qué fila de `party` apunta.
- **La limpieza de huérfanos es mantenimiento operativo** (SQL revisable ejecutado una vez tras la recarga), no código de la ingesta: `party` es identidad compartida con los sondeos y un `DELETE` automático podría llevarse filas referenciadas por `poll_result` (o fallar por FK). El loader nunca borra `party`.
- **Sin fuzzy-matching** (heredado de la 12): normalización exacta o alias explícito. **Ante la duda, no fusionar**: el diff del catálogo es el registro.

## Archivos

| Acción | Archivo |
| --- | --- |
| modificar | `ingestor/src/ingestor/elections/loaders/election.py` — `_resolve_parties` por `PartyResolver` + `load_catalog`; soltar el import/re-export de `slugify` |
| modificar | `ingestor/src/ingestor/polls/loaders/polls.py` — solo si su import de `slugify` pasa por `election.py`: apuntarlo a `ingestor.parties` (una línea; su resolución de rótulos no cambia hasta la feature 14) |
| modificar | `ingestor/tests/test_rules.py` — el import de `slugify` apunta a `ingestor.parties` (el re-export de `election.py` desaparece) |
| crear | `ingestor/tests/test_party_reload.py` — R1–R15 |
| crear | `ingestor/tests/fixtures/party_reload/02200806/`, `…/02201905/`, `…/02202601/` — 02/03/09/10 mínimos (§«Fixtures») |
| modificar | `.agents/data-model.md` · `docs/ingestor/ingesta.md` · `ingestor/AGENTS.md` — §«Documentos» |
| crear | `progress/impl_party_reload.md` — evidencia de la recarga y trazabilidad R ↔ test (convención del arnés; no es un artefacto del acceptance) |

## Código

### `_resolve_parties` (`elections/loaders/election.py`)

La firma no cambia: `_resolve_parties(session, candidacies, candidacy_by_code) -> dict[str, Party]` (la usa `_load_election`, que no se toca). Solo cambia el cuerpo:

```python
def _resolve_parties(
    session: Session,
    candidacies: list[file03.Candidacy],
    candidacy_by_code: dict[str, file03.Candidacy],
) -> dict[str, Party]:
    """Group candidacies by national head through the shared party resolver."""
    heads: dict[str, file03.Candidacy] = {}
    for candidacy in candidacies:
        heads.setdefault(
            candidacy.national_head,
            candidacy_by_code.get(candidacy.national_head, candidacy),
        )

    resolver = PartyResolver(session.scalars(select(Party)), load_catalog())
    parties: dict[str, Party] = {}
    for head_code, head in heads.items():
        label = head.short_name or head.name or f"party-{head_code}"
        party = resolver.resolve(label, code=head_code)
        session.add(party)  # no-op if the row was already persistent
        parties[head_code] = party
    session.flush()
    return parties
```

Detalles que fijan el contrato:

- El agrupado por cabecera nacional (`heads`) es el de hoy, intacto: una fila `party_election` por candidatura, apuntando a la fila del head nacional.
- La etiqueta conserva la reserva actual (`short_name` → `name` → `party-<código>`) y `code=head_code` reproduce el sufijo de colisión del código de cabecera (R23 de la 12); el recorte a 60 caracteres del slug lo aplica el resolver.
- Un resolver por elección: una lectura completa de `Party` (~550 filas) por proceso. Las filas que crea el resolver no se añaden a sesión: las añade el loader (`session.add`, inofensivo si ya era persistente) y el `flush` final las hace visibles para `party_election`.
- `load_catalog()` puede lanzar `IngestError` (catálogo roto): lo captura `ingest_path` por carpeta (outcome `failed`, exit 1), sin cambios.

### `slugify` y sus imports

Con `_resolve_parties` delegado, `election.py` deja de usar `slugify` (la feature 12 movió la implementación a `parties.py` y `re`/`unicodedata` se fueron con ella). Estado final:

- `election.py`: importa `load_catalog` y `PartyResolver` de `ingestor.parties`; **no** re-exporta `slugify`.
- `test_rules.py`: `from ingestor.parties import slugify` (sus casos —`C's`, `MÁS PAÍS`, vacío— no cambian).
- `polls.py`: si quedó importando `slugify` vía `election.py`, apuntarlo a `ingestor.parties` (una línea). Su `_resolve_parties` (rótulos de sondeos) no se toca: es de la feature 14.

## La recarga (operativa)

Desde `ingestor/`, contra el Postgres local (`docker compose up -d --wait` en la raíz). El orden importa: los huérfanos existen hasta el `DELETE`, y la consulta de grupos da 0 solo después.

1. **Conteos pre** (antes de recargar; SQL de §«Evidencia»). Registra `party`, `party_election`, `vote`, `turnout` y `poll_result`.
2. **Recarga**:

   ```sh
   uv run ingestor ingest ../data/raw/congreso --force
   ```

   13 procesos, cada uno en su transacción; salida `processed` para los 13 y exit 0. Registra la salida y los avisos del resolver (`unknown party label`). Si algún proceso falla: parar y documentar (`blocked`); no se parchea código en esta feature.
3. **Conteos post**: `party_election`, `vote`, `turnout` y `poll_result` idénticos a los pre; `party` baja solo con la limpieza.
4. **Limpieza de huérfanos** (SQL de §«Limpieza»), registrando las filas borradas.
5. **Comprobaciones** (§«Comprobaciones»): 0 grupos, 7 filas de marcas, 0 huérfanos.
6. **Iteración (si hiciera falta)**: si quedara un grupo por puntuación, añadir el alias a `data/party_catalog.toml` y reingestar los procesos afectados; repetir desde 2. No es lo esperado (el catálogo cubre el alcance y el resto casa por nombre).

### Conteos pre/post

```sql
SELECT 'party', count(*) FROM silver.party
UNION ALL SELECT 'party_election', count(*) FROM silver.party_election
UNION ALL SELECT 'vote', count(*) FROM silver.vote
UNION ALL SELECT 'turnout', count(*) FROM silver.turnout
UNION ALL SELECT 'poll_result', count(*) FROM silver.poll_result;
```

Los hechos no cambian (la recarga los re-deriva de los mismos ficheros): el criterio es la igualdad de conteos; lo único que cambia es el `party_id` de las candidaturas fusionadas.

### Comprobaciones

Los 13 procesos `congress` nacionales con candidaturas y votos (debe devolver 13):

```sql
SELECT count(*) FROM (
    SELECT e.id
    FROM silver.election e
    JOIN silver.party_election pe ON pe.election_id = e.id
    JOIN silver.vote v ON v.party_election_id = pe.id
    WHERE e.type = 'congress'
      AND e.autonomous_community_ine_code IS NULL
      AND e.municipality_id IS NULL
    GROUP BY e.id
) AS covered;
```

Sin grupos repetidos por puntuación (0 filas):

```sql
SELECT array_agg(slug) AS slugs, count(*)
FROM silver.party
GROUP BY upper(regexp_replace(name, '[^a-zA-Z0-9]', '', 'g'))
HAVING count(*) > 1;
```

BNG, UPL, FIA, Cs, PP, PSOE e IU en una única fila cada uno (7 filas):

```sql
SELECT p.slug, p.name, count(DISTINCT pe.election_id) AS procesos
FROM silver.party p JOIN silver.party_election pe ON pe.party_id = p.id
WHERE upper(regexp_replace(p.name, '[^a-zA-Z0-9]', '', 'g'))
      IN ('BNG','UPL','FIA','CS','PP','PSOE','IU')
GROUP BY p.id ORDER BY p.slug;
```

Huérfanos (debe devolver 0; mismo predicado que el `DELETE`):

```sql
SELECT count(*) FROM silver.party p
WHERE NOT EXISTS (
        SELECT 1 FROM silver.party_election pe WHERE pe.party_id = p.id)
  AND NOT EXISTS (
        SELECT 1 FROM silver.poll_result pr WHERE pr.party_id = p.id);
```

### Limpieza

```sql
DELETE FROM silver.party p
WHERE NOT EXISTS (
        SELECT 1 FROM silver.party_election pe WHERE pe.party_id = p.id)
  AND NOT EXISTS (
        SELECT 1 FROM silver.poll_result pr WHERE pr.party_id = p.id);
```

La exclusión de `poll_result` no es opcional: hoy hay filas de `party` que solo tienen resultados de sondeo (p. ej. `salf`) y la FK `poll_result.party_id → party.id` es `NO ACTION` (un `DELETE` sin exclusión fallaría o, peor, se llevaría hechos de sondeos). Tras la limpieza se repiten las consultas de §«Comprobaciones».

### Evidencia

`progress/impl_party_reload.md` registra: comandos y exit codes; los conteos pre/post de §«Conteos pre/post»; el número de filas borradas; la salida de las consultas de §«Comprobaciones»; los avisos del resolver; y la trazabilidad R ↔ test o evidencia. La ejecución de los comandos y del SQL la hace el implementer y queda registrada aquí; no hay tests de estado automatizados.

## Fixtures

Tres procesos sintéticos mínimos en `ingestor/tests/fixtures/party_reload/` (misma forma que `tests/fixtures/02202307/`; **no** son procesos reales —códigos que no existen en `data/raw/`— para no confundirlos con el bronce). Nombres de fichero con el patrón del adaptador: `<tipo>02<AAMM>.DAT` (glob `{kind}02*.DAT`).

| Carpeta | 02 (fecha) | 03 `short_name` | Nombres de fichero |
| --- | --- | --- | --- |
| `02200806` | `15-06-2008` | `B.N.G.` | `02020806.DAT`, `03020806.DAT`, `09020806.DAT`, `10020806.DAT` |
| `02201905` | `26-05-2019` | `BNG` | `02021905.DAT`, `03021905.DAT`, `09021905.DAT`, `10021905.DAT` |
| `02202601` | `01-01-2026` | `PARTIDO SIN FICHA` | `02022601.DAT`, `03022601.DAT`, `09022601.DAT`, `10022601.DAT` |

Contenido (la fixture `02202307` es el patrón exacto de longitudes y relleno):

- **02** (`{p}{YYYY}{MM}1N99{DD}{MM}{YYYY}09:0020:0014:0018:00`, 41 caracteres; p. ej. `022008061N991506200809:0020:0014:0018:00`). El parser lee proceso, año, mes, ronda, ámbito y fecha.
- **03** (232 caracteres): `02200806` + código `000001` + `short_name` (50) + denominación (150) + `000001` × 3 (cabeceras provincial, regional y nacional). Una candidatura por proceso; su cabecera nacional es ella misma.
- **09** (101 caracteres, una sola mesa): ref `022008061010400101001 A` (CCAA `01`, provincia `04`, municipio `001`, distrito `01`, sección `1`, mesa `A`, como la fixture existente) + censo `0000500` + resto de campos numéricos a ceros + blancos `0000000` + nulos `0000000` + «votos a candidaturas» `0000300` + cola `00000000000000S`.
- **10** (36 caracteres, una fila): la misma ref + código `000001` + votos `0000300` (suma igual al campo de 09: los tres procesos son de años estrictos y una discrepancia abortaría la elección).

Los tres se validan con los parsers (`file02`/`file03`/`file09`/`file10`) al crearlos; el test los ingiere de verdad (si están mal, el test cae).

## Tests — `ingestor/tests/test_party_reload.py`

Integración en los **esquemas de test** (fixture `db` de `conftest.py`; sin `data/raw` ni red) y comprobaciones de documentos. Las comprobaciones R7–R10 sobre `silver` no son tests: se ejecutan a mano con el SQL de §«Comprobaciones» y se registran como evidencia en `progress/impl_party_reload.md` (§«Evidencia»).

Helpers:

```python
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "party_reload"


def _seed_geography(db) -> None:
    """CCAA 01 + provincia 04 (Abla), como la fixture 02202307."""


def _copy_fixtures(tmp_path: Path, *codes: str) -> Path:
    """Copia fixtures/party_reload/<code>/ a tmp_path/congreso/<code>/; devuelve la raíz."""
```

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_two_processes_one_party` | R1, R2, R3 | ingesta de `02200806` + `02201905` (B.N.G. y BNG): outcomes `processed`; una sola fila `party` (slug `bng`, el del catálogo); dos `party_election` con el mismo `party_id` y `short_name` literales; `unknown party label` ausente de `caplog` |
| `test_unknown_head_label_warns` | R4 | ingesta de `02202601`: warning `unknown party label: PARTIDO SIN FICHA -> partido-sin-ficha` y fila creada con el nombre literal |
| `test_force_reload_preserves_facts` | R5, R6 | segunda pasada con `force=True`: `party` no se duplica (misma fila, mismo `id`), y `party_election`/`vote`/`turnout` conservan conteos |
| `test_docs_data_model` | R11, R12 | subcadenas `parties.py` y `party_catalog.toml`; ausencia de `provisional` |
| `test_docs_ingesta` | R13, R14 | subcadenas `parties.py` y `party_catalog.toml`; ausencia de `provisional` |
| `test_docs_ingestor_agents` | R15 | subcadenas `parties.py` y `party_catalog.toml` |

Detalles que fijan el contrato:

- Los tests de integración siembran geografía (CCAA `01` + provincia `04`); el municipio lo crea la propia ingesta. El bronce es `tmp_path` (los ficheros deben colgar de la raíz `RAW_DIR`).
- Las comprobaciones de estado (R7–R10) se ejecutan a mano tras la recarga y la limpieza, con el SQL de §«Comprobaciones», y su salida se registra en `progress/impl_party_reload.md`. Sin test automatizado: en CI se saltarían y su valor es evidencia operativa, no una garantía del código.

## Documentos

- **`.agents/data-model.md`** — bullet de `silver.party` (hoy «la carga provisional agrupa por **cabecera nacional de candidatura** (se curará si hace falta)»): pasa a describir la identidad resuelta por la resolución compartida de `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo → nombre existente → alta con warning), sin la palabra «provisional».

  ```markdown
  - `silver.party`: identidad del partido (nombre, `slug` único, color); la carga de
    elecciones resuelve cada **cabecera nacional de candidatura** con la resolución
    compartida de `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo →
    nombre existente → alta con warning).
  ```

- **`docs/ingestor/ingesta.md`** — paso 4 de «Comportamiento de `ingest`» (hoy «una fila de `party` por grupo (slug único a partir de las siglas…)»):

  ```markdown
  4. **Candidaturas** (`03`): cada **cabecera nacional** se resuelve con la resolución
     compartida de `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo →
     nombre existente → alta con warning): las grafías de la misma marca (`B.N.G.`/`BNG`)
     acaban en una sola fila de `party`, con el slug canónico del catálogo (si el slug
     choca, lleva el código de cabecera). Cada fila del `03` se inserta como
     `party_election`, con su código, siglas y denominación.
  ```

  Y la fila `party` de «Qué queda en `silver`» (hoy «identidad provisional…»):
  «identidad del partido (catálogo `data/party_catalog.toml` vía `parties.py`; `slug` único)».

- **`ingestor/AGENTS.md`** — bullet nuevo en «Ficheros», entre `models.py` y `elections/`: `src/ingestor/parties.py` (resolución compartida de la identidad de partido: normalización → catálogo `data/party_catalog.toml` → nombre existente → alta con warning; la usa el loader de elecciones).

Subcadenas que fijan los tests: `parties.py` y `party_catalog.toml` en los tres documentos; `provisional` ausente en `data-model.md` y `ingesta.md` (hoy aparece solo en esas dos frases que se reescriben).

## Alternativas descartadas

1. **Resolver la identidad dentro del loader** (normalizar/slugify en `election.py`, sin catálogo): duplicaría la identidad —el fallo que la feature 12 corrige— y volvería a partir la marca entre procesos; el resolver es uno solo y compartido.
2. **Borrar los huérfanos desde el loader**: `party` es identidad compartida con los sondeos y la FK de `poll_result` es `NO ACTION`; un `DELETE` automático en la ingesta podría fallar o llevarse hechos de sondeos. El borrado es operación de mantenimiento revisable (este spec fija el SQL exacto).
3. **Reiniciar `party` desde cero** (vaciar y reingerir los 13 procesos): rompería la continuidad de `id` que referencian `poll_result` y otras tablas, y no aporta nada frente a la recarga con catálogo, que converge sola.
4. **Escribir fichas para los 27 grupos del diagnóstico**: la coincidencia por nombre normalizado ya une los pares durante la recarga (los `name` literales casa por NFKD); escribir fichas de más sería curar por duplicado fuera del alcance de la 12.
5. **Tests que ejecuten la recarga real** (subprocess/CLI o escritura sobre `silver`): mutarían la base de la aplicación en `pytest`; la ejecución queda documentada con su evidencia y los tests se limitan a esquemas efímeros y documentos.

## Riesgos y notas

- **Avisos de la recarga**: con el catálogo de la 12 se esperan pocos o ninguno; cualquier `unknown party label` es la señal de añadir ficha (bucle documentado), no un fallo.
- **Slugs fusionados**: desaparecen los slugs de las filas absorbidas; hoy no los consume nadie (`gold` y `web` no existen todavía) y es el momento barato para cambiarlos.
- **2026**: antes de ingerir su `03`, el catálogo necesita las fichas de las marcas nuevas (entre ellas SALF y Aliança.cat, que ya fija la 12); el warning del resolver avisará igualmente.
- **Fallo de la recarga**: si un proceso no cuadra (p. ej. totales estrictos), se para y se documenta `blocked`; la corrección se decide fuera de esta feature.
- **Otros procesos** (Senado, autonómicas): comparten catálogo y resolver sin cambios; el mismo `_resolve_parties` sirve.
