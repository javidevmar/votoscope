# Review — feature 9 `polls_load`

**Veredicto:** APPROVED

Rama `feature/polls-load` (stack sobre `feature/polls-adapter`), working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). `./init.sh` re-ejecutado por el reviewer: verde — arnés + specs, `ruff check`/`ruff format --check` limpios, **125 tests** (26 nuevos de `test_polls_load.py`, todos verdes y **sin skips**: Postgres levantado en `:5434`, esquemas `polls_test_*` reales) y `alembic check` sin drift.

Diff revisado (solo la feature 9): `ingestor/src/ingestor/polls/loaders/{__init__.py,polls.py}` (nuevos), `ingestor/src/ingestor/cli.py` (subcomando `ingest-polls`), `ingestor/tests/conftest.py` (nuevo), `ingestor/tests/test_polls_load.py` (nuevo, 26 tests), `ingestor/tests/fixtures/wikipedia_polls/{load_small,load_other}.wikitext` (nuevas), `docs/ingestor/ingesta.md` y `ingestor/AGENTS.md`. Fuera de alcance y excluidos: `specs/010_polls_schedule/`, `opencode.json`, `feature_list.json`, `progress/current.md` y `data/raw/` (gitignored). `specs/009_polls_load/tasks.md` revisado (solo checkboxes: 16/16).

Verificación adicional del reviewer (sondas puntuales, además del suite):

- **Snapshot real en seco** (`data/raw/polls/wikipedia-en/2026-general/1380713440.wikitext`, gitignored): `parse_polls` + `_validate` → **575 filas, 6125 resultados, sin errores de validación**; únicos warnings, ambos del adaptador y contemplados (`unknown party column: FA`, `unparseable turnout: 66–67`). Confirma la nota del impl y que las validaciones no rechazan la página real.
- **Higiene**: el suite no deja esquemas `polls_test_*` filtrados (teardown de `conftest.py` los dropea; comprobado contra `information_schema.schemata`); `git status` sin basura (solo artefactos esperados); grep sin `print()`/TODO en los ficheros de la feature.
- **Contraste con el diseño**: firmas de `design.md` §Firmas presentes (`PollsOutcome`, `ingest_polls_path`, `ingest_snapshot`, `load_polls`, `resolve_poll_elections` + internos); flujo de `ingest_polls_path` (resolución → `_snapshot_files` ordenado por revid → `try/except IngestError` por fichero) y `ingest_snapshot` (guard → registro → parseo → transacción de plata → `processed`) coinciden paso a paso; el patrón de transacciones separadas (bronce/estado aparte, plata única) es el del loader de elecciones (`election.py` L93, L163–171).

## Trazabilidad requirements ↔ tests

Tests: `ingestor/tests/test_polls_load.py` (26, todos verdes; fixtures en `tmp_path` + cadenas inline; sin red, `data/raw/` ni `refs/`).

- R1: [x] `test_cli_registers_and_loads` (L124–136: sha256 real, `size_bytes`, `source = wikipedia-en`, `file_path` relativo a `RAW_DIR`, `processed`).
- R2: [x] `test_cli_registers_and_loads` (todas las filas de plata escritas) + `_assert_silver_intact` (L449–454) en los 4 tests de fallo: sin filas parciales tras rollback.
- R3: [x] `test_cli_registers_and_loads` (L138–141) + `test_existing_party_and_pollster_reused` (L192–210: mismo id, sin duplicados, nombre intacto).
- R4: [x] `test_cli_registers_and_loads` (L143–147: alta de `salf` con «Se Acabó La Fiesta») + `test_existing_party_and_pollster_reused`.
- R5: [x] `test_cli_registers_and_loads` (L149–166: `pollster_id`, `source`, `election_type = congress`, `election_id` nulo, fechas, muestra, turnout, `revision_id` 200 leído del nombre).
- R6: [x] `test_cli_registers_and_loads` (L168–186 vía `_results`: `poll_id`, `party_id`, `pct`, `seats_min`, `seats_max`).
- R7: [x] `test_replacement_deletes_previous_polls` (L213–229: borrado total; `pollster`/`party` conservados).
- R8: [x] `test_cli_registers_and_loads` (L136: `processed` tras el commit).
- R9: [x] `test_skip_processed` (L235–250: `skipped`, ids de `poll` sin cambios, un solo registro en bronce, exit 0).
- R10: [x] `test_guard_ignores_older_revision` (L253–266: warning «older than», silver intacto, 100 **sin fila en bronce**, exit 0).
- R11: [x] `test_force_reloads_processed_and_older` (L269–279: recarga `processed` y anterior; silver retrocede a 100).
- R12: [x] `test_resolution_links_after_fieldwork` (L326–358: misma fecha excluida por estricto, primera posterior, CCAA/municipio/otro tipo ignorados).
- R13: [x] `test_resolution_leaves_unmatched_and_null_fieldwork` (L361–374: sin candidata → nulo, 0 enlaces, sin error).
- R14: [x] `test_resolution_leaves_unmatched_and_null_fieldwork` (sin `fieldwork_end` → nulo).
- R15: [x] `test_resolution_runs_without_pending_snapshots` (L377–392: directorio vacío, enlaza igual, exit 0).
- R16: [x] `test_resolution_is_idempotent` (L395–411: segunda pasada 0 enlaces, no relinkea).
- R17: [x] `test_missing_signature_fails` (L457–475: celda vacía y `/(Medio)` → `no signature`).
- R18: [x] `test_fewer_than_two_parties_fails` (L478–488: `?` no produce resultado; un solo partido con valor).
- R19: [x] `test_pct_and_seats_out_of_range_fail` (L491–535: pct 150; escaños 400; `200/100`).
- R20: [x] `test_pct_sum_warns_and_loads` (L538–555: 60+45 → warning «add up to» y carga `processed`).
- R21: [x] `test_empty_snapshot_fails_and_keeps_silver` (L558–561: sin sondeos → `no polls`).
- R22: [x] los 4 tests de fallo vía `_assert_failed` (L433–446: outcome `failed`, mensaje, bronce `failed`) + `_assert_silver_intact` (rollback).
- R23: [x] `test_cli_registers_and_loads` (fichero) + `test_directory_processes_in_revision_order` (L594–604: directorio, orden por revid).
- R24: [x] `test_cli_default_path_processes_recursively` (L607–612) + `test_resolution_runs_without_pending_snapshots` (directorio vacío sin error).
- R25: [x] `test_cli_exit_codes` (L586–591: fallo → 1, sin novedades → 0) + `test_skip_processed`, `test_guard_ignores_older_revision`, `test_resolution_runs_without_pending_snapshots`.
- R26: [x] `test_missing_path_raises` (L567–569).
- R27: [x] `test_snapshot_outside_raw_dir_raises` (L572–575).
- R28: [x] `test_bad_snapshot_filename_raises` (L578–583: `notarevid.wikitext`).
- R29: [x] `test_docs_ingesta` (L663–673) + diff de `docs/ingestor/ingesta.md` (sección del comando, «Comportamiento de `ingest-polls`», filas de `silver`).
- R30: [x] `test_docs_ingestor_agents` (L676–679) + diff de `ingestor/AGENTS.md` (bullet de `polls/` con `loaders/polls.py`, comando en «Comandos» y bullet de sondeos).
- R31: [x] `test_unknown_label_creates_party_with_warning` (L618–657: `FA` → warning + `fa`/«FA»; segunda carga lo reutiliza).

Tests de infraestructura (no mapean a un R, documentados en el impl): `test_database_fixture` (L59–65), `test_load_fixtures_parse` (L71–86).

## Tasks completas

- T1–T16: [x] — todas marcadas en `specs/009_polls_load/tasks.md`; diff = solo checkboxes (16/16). Sin tasks `[ ]`. T6/T8/T10/T12/T14 no-ops justificados en `progress/impl_polls_load.md` §Notas (T4 ya cubría su comportamiento; sus tests quedaron verdes sin tocar código).

## Checkpoints

- C1: [x] — piezas base del arnés y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#9; validado por `init.sh` §3); features `done` con el suite en verde (125/125); `progress/current.md` describe la sesión activa (feature 9, pendiente de reviewer + gate).
- C3: [x] — sin cambios de modelo (ni `models.py`, ni drawio, ni Alembic; `alembic check` sin drift → los tres sitios N/A); sin DDL a mano; sin dependencias nuevas (`pyproject.toml`/`uv.lock` intactos; se reutilizan `sha256`/`slugify`, `SOURCE` y el adaptador de la 8); capas respetadas (`polls/loaders/polls.py` persistencia, CLI fino con `SessionLocal` inyectado, flujo bronce → plata); logging por módulo con formateo perezoso y `LOG_LEVEL` vía `configure_logging`; sin `print()`/TODO (grep en los ficheros de la feature).
- C4: [x] en local — pytest 125/125 (26 nuevos, ninguno saltado), `ruff check`/`ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para `feature/polls-load` (sin commits aún, por diseño del flujo); el workflow ejecuta exactamente estos gates y se disparará con los commits/push post-OK.
- C5: [ ] pendiente del cierre post-veredicto — sin archivos temporales ni basura en `git status` (solo los artefactos esperados); `progress/history.md` al día al cerrar la sesión; `feature_list.json` coherente; commits atómicos pendientes del OK del usuario (por diseño).
- C6: [x] — `specs/009_polls_load/` con los 3 archivos; EARS con ids estables (R1–R31) y tabla acceptance↔R; T1–T16 `[x]`; mapa de trazabilidad R1–R31 en `progress/impl_polls_load.md` (verificado línea a línea contra el suite).

## Observaciones no bloqueantes (no exigen cambios)

1. `ingest-polls` **sin ruta** y `RAW_DIR/polls/` inexistente → `IngestError` y exit 1 (R26 aplicado a la ruta por defecto; el `design.md` lo fija así y R24/R25 se verifican con directorio vacío existente). El ciclo «sin novedades» de la feature 10 ejecuta `fetch-polls` primero (que crea el directorio), así que no afecta; anotarlo en el job si se invocara `ingest-polls` en solitario antes del primer fetch.
2. Una excepción **no-`IngestError`** en la transacción de plata (p. ej. `IntegrityError` de un CHECK no cubierto por `_validate`, como turnout fuera de rango) se marca `failed` y se re-lanza, pero escapa de `ingest_polls_path`/CLI (que solo capturan `IngestError`) → traceback con exit 1 en vez de resumen limpio. Mismo patrón que el loader de elecciones (`election.py` L93/L163–171); fuera del alcance de R17–R22 (el CHECK es la red de seguridad).
3. R31: dos rótulos crudos distintos que slugifiquen al mismo slug (p. ej. `FA` y `fa`) colisionarían en una sola fila de `party`; comportamiento provisional por diseño (lo cura el catálogo de party-norm, feature 14) y sin caso en la página real (sonda: `results` con rótulo crudo = `{}`).

## Cambios requeridos

Ninguno.
