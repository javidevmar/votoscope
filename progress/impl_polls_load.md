# Implementación — `polls_load` (feature 9)

- Spec: [`specs/009_polls_load/`](../specs/009_polls_load/) (R1–R31, T1–T16).
- Rama: `feature/polls-load`. Sin commits: cambios en el working tree.
- Sin cambios de modelo (ERD ↔ `models.py` ↔ Alembic no aplican); sin dependencias nuevas.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/loaders/__init__.py` |
| crear | `ingestor/src/ingestor/polls/loaders/polls.py` — loader (bronce + plata) y pase de resolución |
| modificar | `ingestor/src/ingestor/cli.py` — subcomando `ingest-polls` (`[ruta]`, `--force`, resumen, exit codes) |
| crear | `ingestor/tests/conftest.py` — esquemas Postgres de test (`schema_translate_map`), `skip` sin BD |
| crear | `ingestor/tests/test_polls_load.py` — 26 tests (R1–R31 + infra) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/load_small.wikitext`, `load_other.wikitext` |
| modificar | `docs/ingestor/ingesta.md` — comando `ingest-polls`, «Comportamiento de `ingest-polls`», filas de `silver` (R29) |
| modificar | `ingestor/AGENTS.md` — `loaders/polls.py`, comando `ingest-polls`, bullet de sondeos (R30) |

## Trazabilidad R ↔ test

Todos los tests viven en `ingestor/tests/test_polls_load.py` (BD real en esquemas aislados).

| R | Test(s) |
| --- | --- |
| R1 | `test_cli_registers_and_loads` (sha256 real, tamaño, `source = wikipedia-en`, ruta relativa) |
| R2 | `test_cli_registers_and_loads` (todas las filas de plata en un commit) + `test_missing_signature_fails`/`test_fewer_than_two_parties_fails`/`test_pct_and_seats_out_of_range_fail`/`test_empty_snapshot_fails_and_keeps_silver` (`_assert_silver_intact`: rollback sin filas parciales) |
| R3 | `test_cli_registers_and_loads`, `test_existing_party_and_pollster_reused` (mismo id, sin duplicados, nombre intacto) |
| R4 | `test_cli_registers_and_loads` (alta de `salf` con «Se Acabó La Fiesta»), `test_existing_party_and_pollster_reused` |
| R5 | `test_cli_registers_and_loads` (`pollster_id`, `source`, `election_type = congress`, `election_id` nulo, fechas, muestra, turnout, `revision_id`) |
| R6 | `test_cli_registers_and_loads` (`poll_id`, `party_id`, `pct`, `seats_min`, `seats_max`) |
| R7 | `test_replacement_deletes_previous_polls` (borrado total; `pollster`/`party` conservados) |
| R8 | `test_cli_registers_and_loads` (`processed` en bronce) |
| R9 | `test_skip_processed` (segunda ejecución: `skipped`, sin escrituras, exit 0) |
| R10 | `test_guard_ignores_older_revision` (warning «older than», `silver` intacto, sin fila en bronce, exit 0) |
| R11 | `test_force_reloads_processed_and_older` (`--force` recarga `processed` y anterior; `silver` retrocede) |
| R12 | `test_resolution_links_after_fieldwork` (primera nacional posterior, estricta; ignora CCAA/municipio/otro tipo) |
| R13 | `test_resolution_leaves_unmatched_and_null_fieldwork` (sin candidata → nulo, sin error) |
| R14 | `test_resolution_leaves_unmatched_and_null_fieldwork` (sin `fieldwork_end` → nulo) |
| R15 | `test_resolution_runs_without_pending_snapshots` (directorio vacío: enlaza igual, exit 0) |
| R16 | `test_resolution_is_idempotent` (segunda pasada: 0 enlaces, no relinkea) |
| R17 | `test_missing_signature_fails` (celda de firma vacía y `/(Medio)`) |
| R18 | `test_fewer_than_two_parties_fails` |
| R19 | `test_pct_and_seats_out_of_range_fail` (pct 150, escaños 400, `200/100`) |
| R20 | `test_pct_sum_warns_and_loads` (60+45: warning «add up to» y carga `processed`) |
| R21 | `test_empty_snapshot_fails_and_keeps_silver` |
| R22 | `test_missing_signature_fails`, `test_fewer_than_two_parties_fails`, `test_pct_and_seats_out_of_range_fail`, `test_empty_snapshot_fails_and_keeps_silver` (outcome `failed`, bronce `failed`, `_assert_silver_intact`) |
| R23 | `test_cli_registers_and_loads` (fichero), `test_directory_processes_in_revision_order` (directorio, orden por revid) |
| R24 | `test_cli_default_path_processes_recursively` (sin ruta: `RAW_DIR/polls` recursivo), `test_resolution_runs_without_pending_snapshots` |
| R25 | `test_cli_exit_codes` (fallo → 1; sin novedades → 0), `test_skip_processed`, `test_guard_ignores_older_revision`, `test_resolution_runs_without_pending_snapshots` |
| R26 | `test_missing_path_raises` |
| R27 | `test_snapshot_outside_raw_dir_raises` |
| R28 | `test_bad_snapshot_filename_raises` |
| R29 | `test_docs_ingesta` (`ingest-polls`, `wikipedia-en`, `revision_id`, `failed`, `pollster`, `poll_result`) |
| R30 | `test_docs_ingestor_agents` (`ingest-polls`, `polls.py`) |
| R31 | `test_unknown_label_creates_party_with_warning` (`FA` → `fa`/«FA» + warning; segunda carga lo reutiliza) |

Tests de infraestructura (no mapean a un R): `test_database_fixture` (esquemas de test + `select(1)`), `test_load_fixtures_parse` (contenido de las fixtures).

## Notas de implementación

- **T6, T8, T10, T12 y T14 fueron no-ops**: la implementación de T4 ya cubría reutilización/reemplazo, guard, resolución, validaciones y rutas; sus tests quedaron verdes sin tocar código.
- **Tests añadidos sobre el listado del `design.md`**: `test_unknown_label_creates_party_with_warning` (R31, que no estaba asignado a ninguna task), `test_cli_default_path_processes_recursively` (R24 de verdad: ruta por defecto recursiva) y `test_directory_processes_in_revision_order` (fija el orden por `revid` del diseño; con `99`/`200` el orden lexicográfico sería el contrario).
- **Orden por `revid`**: se procesan los snapshots de un directorio de menor a mayor revisión para que el guard no marque como «anterior» uno recién procesado en la misma ejecución.
- **Flush explícito en tests**: el flush del ORM no ordena por FK sin `relationship()`, así que el seed de geografía hace `flush` entre CCAA, provincia y municipio.
- **Verificación manual con el snapshot real** (`data/raw/polls/wikipedia-en/2026-general/1380713440.wikitext`, gitignored): `parse_polls` + `_validate` → 575 filas, 6125 resultados, sin errores de validación (los warnings son del adaptador: columna `FA`, turnout `66–67`). No se ha cargado en los esquemas reales: eso es la feature 11.

## Puerta (T16)

- `uv run pytest`: 125 pasan (26 de esta feature).
- `uv run ruff check .` y `uv run ruff format --check .`: limpios.
- `uv run alembic check`: sin drift.
- `./init.sh`: verde (Postgres levantado, así que los tests de BD corren; no se saltan).
