# Implementación — `polls_adapter` (feature 8)

- **Estado:** implementada; `./init.sh` en verde (25 tests nuevos + 74 previos = 99; ruff check/format y `alembic check` limpios).
- **Rama:** `feature/polls-adapter` (stack sobre `feature/polls-lexer`). Sin commits: los cambios quedan en el working tree para el reviewer y el OK del usuario.
- **Spec:** [`specs/008_polls_adapter/`](../specs/008_polls_adapter/); tasks T1–T19 marcadas `[x]`.
- **Sin cambios de modelo** (ERD ↔ `models.py` ↔ migración no aplican). Sin dependencias nuevas (solo stdlib).

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/adapters/__init__.py` |
| crear | `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py` |
| crear | `ingestor/tests/test_wikipedia_polls.py` (25 tests) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/real_2026_head.wikitext` |
| crear | `ingestor/tests/fixtures/wikipedia_polls/real_2023_tail.wikitext` |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_dates.wikitext` |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_cells.wikitext` |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_columns.wikitext` |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_out_of_scope.wikitext` |
| modificar | `ingestor/AGENTS.md` — bullet de `polls/` documenta `adapters/wikipedia_polls.py` (R29) |

## Snapshot y fixtures (T1)

- Snapshot real: `uv run ingestor fetch-polls` → revid **1380713440** (2026-10-17T11:34:38Z), en `data/raw/polls/wikipedia-en/2026-general/1380713440.wikitext` (gitignored; no versionado).
- **`real_2026_head.wikitext`** (332 líneas): ensamblado de `====Voting intention estimates====` + `=====2026 (before FA)=====` hasta la celda `Lead` de la fila oficial del CIS (líneas 13 + 54–383 del snapshot). **Decisión de corte**: la subsección `2026 (after FA)` (vacía en esa revisión) queda fuera porque su columna `FA` no está en el mapeo y dispararía un `unknown party column` que rompería la «ausencia de warnings de columna» que el design fija para este recorte (`test_color_header_row_ignored`). El design describe el corte como «desde … hasta …»; se materializa como ensamblado de tramos (mismo criterio que el design fija para `real_2023_tail`).
- **`real_2023_tail.wikitext`** (76 líneas): ensamblado de `====Voting intention estimates====` + `=====2023=====` con la apertura y las dos filas de cabecera (líneas 13 + 10150–10182) + cola (última fila `EM-Analytics/Electomanía` `24–25 Jul`, separadora, fila `#EFEFEF` del resultado de 2023, separadora y `|}`; líneas 11441–11481). Corte literal, sin retocar.
- **Sintéticas**: `synthetic_dates` (cruce de año, día único, `?`; muestras/participaciones), `synthetic_cells` (bold, `<2.0`+`0`, `–`, nota sola, `<br />`, solo pct, `?`+escaños, `?` sola), `synthetic_columns` (fijas desordenadas `Turnout`/`Sample size`, wikilinks con alt/`link=`/plano, SALF/Aliança.cat/AA por `link=`, FA desconocida, Lead), `synthetic_out_of_scope` (tabla señuelo en `Voting preferences`). En `synthetic_out_of_scope` la tabla válida vive bajo `=====2026=====` (el test exige que `poll_tables` la devuelva; el design lo describía sin la subsección).
- Aviso esperado del lexer: `real_2026_head` es un corte a mitad de tabla → `unterminated table at end of input` (WARNING del lexer, no del adaptador). Los tests no lo consideran un warning del adaptador (`test_color_header_row_ignored` comprueba ausencia de warnings de columna).

## Notas de secuencia TDD

- T5 implementó, además del plan de columnas y la firma, la lectura de muestra/participación y el `pct` de las celdas de partido: era el mínimo para que los tests de T4 (`test_synthetic_columns_mapping`, `test_fixed_columns_by_label`) quedaran verdes. T11 y T15 completaron `?`/warnings de `_parse_sample`/`_parse_turnout` con sus tests de T10/T14 ya escritos.
- Los guards de robustez (`not a polls table`, `column count mismatch`) se implementaron junto al plan (T5) y al bucle de filas (T7) porque eran necesarios para leer las fixtures reales; T14 fijó sus tests y T15 completó los warnings de muestra/participación.

## Delta R8 (T19, 2026-10-17)

- **Cambio**: la columna de partido desconocida ya no se descarta. En `_column_plan`, el rótulo resuelto no mapeado pasa a `parties[index] = label` (rótulo crudo como clave de `results`), manteniendo el warning `unknown party column: %s`; las celdas se procesan como las de una columna conocida. La resolución de identidad queda para el loader (feature 9).
- **Tests**: `test_unknown_column_warns_and_ignored` → `test_unknown_column_warns_and_kept` (warning con el rótulo + `row.results["FA"].pct == Decimal("5.0")`); `test_synthetic_columns_mapping` incluye `"FA"` en el orden de columnas. La fixture `synthetic_columns` ya daba valor `5.0` a `FA`: sin cambios.
- **Spec**: R8 y el plan de columnas/contrato de `results` de `design.md` ya reflejaban el comportamiento nuevo; sin cambios de código fuera de `_column_plan`/`_read_row` (rename `slug` → `key` y docstring de `_Plan`).

## Trazabilidad

| R | Test(s) |
| --- | --- |
| R1 | `test_real_head_first_rows` (14 filas = una por fila de datos, campos y `results` en orden de columna), `test_real_cis_block`, `test_real_2023_tail_skips`, `test_synthetic_dates`, `test_party_cells` |
| R2 | `test_poll_tables_scope` (señuelo fuera), `test_poll_tables_years`, `test_poll_tables_all_subsections_and_tables` (varias subsecciones del mismo año y varias tablas), `test_real_head_first_rows` |
| R3 | `test_color_header_row_ignored` (sin warnings de columna en el recorte real; la primera fila de datos es SocioMétrica, no la de colores) |
| R4 | `test_fixed_columns_by_label` (fijas desordenadas: `Turnout` antes que `Sample size`) |
| R5 | `test_synthetic_columns_mapping` (orden distinto; rótulos por wikilink alt/`link=`/plano), `test_real_head_first_rows` |
| R6 | `test_party_columns_mapping` (15 rótulos → slugs), `test_synthetic_columns_mapping` |
| R7 | `test_party_columns_mapping` (`salf`/«Se Acabó La Fiesta», `alianca-cat`/«Aliança Catalana»), `test_synthetic_columns_mapping` |
| R8 | `test_unknown_column_warns_and_kept` (`FA` → warning con el rótulo + resultado con clave `FA`), `test_synthetic_columns_mapping` (`FA` en `results` en orden de columna) |
| R9 | `test_lead_column_ignored_without_warning` (`Lead` sin warning y sin resultado) |
| R10 | `test_real_2023_tail_skips` (separadoras `colspan` fuera, sin warnings) |
| R11 | `test_real_2023_tail_skips` (fila `#EFEFEF` del resultado de 2023 fuera) |
| R12 | `test_party_cells` (número, `<2.0`, `–`, nota, `?`), `test_real_head_first_rows` |
| R13 | `test_party_cells` (`N`, `N/M`, `?`, sin segunda línea), `test_real_head_first_rows` |
| R14 | `test_party_cells` (`–`, nota sola y `?` sola no producen resultado; `<2.0`+`0` y `?`+`7` sí), `test_real_head_first_rows` |
| R15 | `test_parse_date_matrix` (`5 Oct` → inicio = fin), `test_synthetic_dates` |
| R16 | `test_parse_date_matrix` (`10–11 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`, `31 Dec–3 Jan`), `test_synthetic_dates` (cruce → año−1), `test_real_cis_block` (fecha compartida por `rowspan`) |
| R17 | `test_parse_date_matrix` (`?` → nulas), `test_synthetic_dates` |
| R18 | `test_sample_and_turnout` (`1,000` → 1000, `?` → nulo), `test_synthetic_dates`, `test_real_head_first_rows` |
| R19 | `test_sample_and_turnout` (`67.6`/`66` → `Decimal`, `?` → nulo), `test_synthetic_dates`, `test_real_head_first_rows` |
| R20 | `test_real_cis_block` (tres filas del CIS, `source` literal), `test_pollster_name_extraction`, `test_real_head_first_rows` (una fila por fila de datos) |
| R21 | `test_pollster_name_extraction` (`SocioMétrica/El Español` → `SocioMétrica`; `CIS (Target Point)` → `CIS`; `More in Common`), `test_real_cis_block` |
| R22 | `test_parse_date_matrix` (basura → warning `unparseable date` + nulas), `test_garbage_cells_warn_and_null` (warnings `unparseable sample size`/`turnout`/`pct` + nulos) |
| R23 | `test_row_mismatch_warns_and_skips` (warning `column count mismatch` + fila saltada) |
| R24 | `test_table_without_fixed_labels_warns_and_skips` (warning `not a polls table` + tabla saltada) |
| R25 | `test_missing_section_warns_and_empty` (warning `section not found` + lista vacía) |
| R26 | `test_election_type` (`ELECTION_TYPE == "congress"`) |
| R27 | `test_module_is_stdlib_only_and_pure` (imports ⊆ stdlib ∪ `ingestor.polls.parsers.wikitext`; sin `urlopen`/`socket`/`requests`/`httpx`/`open(`/`sqlalchemy`/`SessionLocal`) |
| R28 | `test_fixtures_present` (las seis fixtures) + todos los tests parsean fixtures o cadenas inline, sin red, `data/raw/` ni `refs/` |
| R29 | `test_docs_ingestor_agents` (subcadenas `wikipedia_polls.py` y `sondeos` en `ingestor/AGENTS.md`) |

## Verificación

- `./init.sh` → verde (99 tests, ruff check + format, `alembic check` sin drift).
- `uv run pytest ingestor/tests/test_wikipedia_polls.py` → 25 passed.

## Pendiente (para el reviewer / siguiente feature)

- Feature 9 (`polls_load`, `specs/009_polls_load/` sin trackear): consume `ELECTION_TYPE`, `PARTY_COLUMNS` y `parse_polls`; el `revision_id` viene del nombre del snapshot.
- Commits atómicos y PR: tras el OK del usuario (no hechos en esta sesión).
