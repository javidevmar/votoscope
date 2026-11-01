# Review — feature 14 `party_polls` (iniciativa `party-norm`)

**Veredicto:** APPROVED

Rama `feature/party-polls` (piso 3 del stack), cambios en el working tree sin commitear (correcto: el commit llega tras el OK del usuario). Revisión contra `specs/014_party_polls/`, `.agents/`, `CHECKPOINTS.md` y el `silver` local.

Verificaciones independientes ejecutadas por el reviewer (además de la suite):

- `./init.sh` **verde** de principio a fin: `uv sync`, `ruff check`, `ruff format --check`, `pytest` **199 passed sin skips** (los tests de estado usan el Postgres local), `alembic check` sin drift, exit 0.
- Estado real de `silver` consultado directamente (sin fiarse del informe): `party` **521**, `poll` **575**, `poll_result` **6.125**; los tres snapshots de `bronze.ingestion` (`1380713440`, `1380777984`, `1380859635`) están `processed`. Coincide con los conteos pre/post de `progress/impl_party_polls.md`: la recarga no cambió los conteos.
- Consulta de encaje de las quince marcas (`design.md` §«Comprobación real»): las trece con candidatura tienen exactamente **1** `poll_result` distinto y **1** `party_election` distinto; `salf` y `alianca-cat` tienen **1** resultado y **0** candidaturas (no están en el `03`). Cero filas duplicadas por slug.
- Cross-check independiente del catálogo: las quince etiquetas de `PARTY_LABELS` resuelven a los slugs fijados (`labels mismatched: {}`), `lookup(<slug>)` devuelve su propia ficha para **las 79 fichas** (`self-lookup mismatched: []`) y `C's` resuelve a `cs`; `FA` no tiene ficha (sigue el camino de rótulo crudo).
- `grep` en el código de aplicación: `PARTY_COLUMNS`, `PartyColumn`, `_PARTY_NAMES` y `_party_slug` no aparecen fuera de specs, informes y asserts de test. El adaptador no importa SQLAlchemy ni abre red; el loader importa `PartyResolver`, `load_catalog` y `slugify` de `ingestor.parties`.
- Sin cambios en `models.py`, `docs/db/schema.drawio` ni migraciones (`git status` solo muestra los ficheros previstos); `git diff --check` limpio, sin `print()` ni TODOs nuevos.

## Trazabilidad requirements ↔ tests

- R1: [x] `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog` (catálogo real), `::test_parse_resolves_label_outside_mapping` (`parse_polls` resuelve `C's` con `Catalog.lookup`, sin mapeo propio) y `::test_unknown_column_warns_and_kept` (catálogo inyectado). Código: `wikipedia_polls.py:23,142,199-218`.
- R2: [x] `test_wikipedia_polls.py::test_parse_resolves_label_outside_mapping` — la clave es `catalog.lookup("C's").slug` (`cs`); `::test_synthetic_columns_mapping` fija las claves de una tabla con el catálogo real.
- R3: [x] `test_wikipedia_polls.py::test_unknown_column_warns_and_kept` — con un catálogo de `tmp_path` sin ficha para `FA`, la clave es el rótulo crudo y `row.results["FA"]` conserva su porcentaje.
- R4: [x] `test_wikipedia_polls.py::test_unknown_column_warns_and_kept` — warning `unknown party column` con el rótulo (`FA`) y la carga sigue (el test obtiene la fila completa). Código: `wikipedia_polls.py:214-216`.
- R5: [x] `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog` — las quince etiquetas → slugs fijados; `lookup(<slug>) == ficha` para todas las fichas; nombres de `SALF`/`Aliança.cat` contrastados. Cross-check independiente del reviewer: 0 mismatches.
- R6: [x] `test_wikipedia_polls.py::test_mapping_table_removed` — `hasattr(wikipedia_polls, "PARTY_COLUMNS"/"PartyColumn")` es falso; grep confirma ausencia en el módulo.
- R7: [x] `test_wikipedia_polls.py::test_module_is_stdlib_only_and_pure` — imports por AST ⊆ stdlib + `ingestor.*`, con `ingestor.parties` admitido; prohibidos `urlopen`, `socket`, `requests`, `httpx`, `open(`, `sqlalchemy` y `SessionLocal`. El adaptador no toca BD ni red (solo lee el catálogo empaquetado vía `load_catalog`).
- R8: [x] `test_party_polls.py::test_loader_resolves_catalog_only_label` — snapshot con `PP` y `C's`: crea `pp` y `cs` con los nombres de las fichas, sin `unknown party column` ni `unknown party label`; `test_polls_load.py::test_cli_registers_and_loads` contrasta los nombres de `pp`/`psoe` con `load_catalog()`. Código: `polls.py:305-311`.
- R9: [x] `test_party_polls.py::test_loader_has_no_local_party_mapping` — sin `_PARTY_NAMES` ni `_party_slug`; grep confirma que no quedan en el loader.
- R10: [x] `test_polls_load.py::test_unknown_label_creates_party_with_warning` — `FA` sin ficha ni nombre existente crea `Party(name="FA", slug="fa")` con warning `unknown party label`; el formato exacto `unknown party label: <clave> -> <slug>` está fijado en `test_parties.py` (feature 12) y lo emite el resolver compartido (`parties.py:152`).
- R11: [x] `test_party_polls.py::test_poll_and_election_share_party_row` — la candidatura `B.N.G.` de `02200806` y la columna `BNG` del sondeo apuntan al mismo `party.id` (`bng`); verificado además en el `silver` real: 13/13 marcas con candidatura tienen 1 fila distinta en cada lado.
- R12: [x] `test_party_polls.py::test_poll_and_election_share_party_row` (segunda carga con revisión 201: `count(party)` no crece), `test_polls_load.py::test_existing_party_and_pollster_reused` (reutiliza por `id`) y `::test_unknown_label_creates_party_with_warning` (segunda carga reutiliza `fa`).
- R13: [x] `test_party_polls.py::test_docs_ingesta_polls_mapping` — `parties.py` y `party_catalog.toml` presentes en la sección «Comportamiento de `ingest-polls`»; texto en `docs/ingestor/ingesta.md:111-117`.
- R14: [x] `test_party_polls.py::test_docs_ingesta_polls_mapping` — «slugs del mapeo» ausente del documento; `grep` independiente sin coincidencias.
- R15: [x] tests en `ingestor/tests/test_party_polls.py` (loader, sin mapeo local, coincidencia sondeos↔elecciones, documentos), actualización de `test_wikipedia_polls.py` (adaptador) y `test_polls_load.py` (nombres por catálogo); ningún test del adaptador usa el fixture `db` y no hay red ni `data/raw` en los tests nuevos.

## Tasks completas

`specs/014_party_polls/tasks.md`: T1–T8 todas `[x]`, sin justificaciones pendientes.

- T1: [x]
- T2: [x]
- T3: [x]
- T4: [x]
- T5: [x]
- T6: [x]
- T7: [x]
- T8: [x]

## Checkpoints

- C1: [x] piezas base y los 4 agentes presentes (`init.sh` §2 los verifica); `./init.sh` exit 0.
- C2: [x] una sola `in_progress` (feature 14); 199 tests verdes incluidas las features previas; `progress/current.md` describe la sesión activa (12–14 en serie).
- C3: [x] sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican; `alembic check` sin drift); sin DDL a mano; arquitectura respetada (el adaptador resuelve y el loader persiste con `PartyResolver`, sin duplicar la lógica de `parties.py`); sin dependencias nuevas; logging por `getLogger(__name__)` con warning perezoso; sin `print()` ni TODOs.
- C4: [x] `pytest` (199 passed, sin skips, estado real contra Postgres), `ruff check`, `ruff format --check` y `alembic check` verdes en local. CI (`ingestor.yml`) no verificable aún: la rama no está pusheada por diseño (commits tras el OK del usuario); el equivalente local está verde.
- C5: [x] sin archivos temporales ni basura (solo los ficheros previstos y los dos nuevos: test e informe); feature 14 en `in_progress` (estado correcto antes del OK del usuario). `progress/history.md` tiene la última sesión cerrada; la entrada de esta sesión y los commits atómicos quedan pendientes por diseño del flujo, al cerrar.
- C6: [x] carpeta con `requirements.md`, `design.md` y `tasks.md`; EARS estricto con un `DEBE`/`NO DEBE` por requirement; tasks `[x]`; R1–R15 cubiertos por tests concretos y mapa en `progress/impl_party_polls.md`.

## Cambios requeridos

Ninguno. Alcance respetado: adaptador y loader de sondeos, los tres ficheros de test y `docs/ingestor/ingesta.md`; sin tocar modelo, CLI, catálogo, dependencias ni `party_election`.

Observación no bloqueante: `ingestor/AGENTS.md:25` dice que `parties.py` «la usa el loader de elecciones»; tras esta feature también lo usa el loader de sondeos. La frase sigue siendo cierta y el `design.md` aprobado dejó ese fichero fuera de alcance; si se toca en una pasada de documentación futura, conviene añadir el loader de sondeos.
