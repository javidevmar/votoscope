# Implementación — feature 19 `gold_matviews`

- **Rama:** `feature/gold_matviews` (sin commits; cambios en el working tree).
- **Spec:** [`specs/019_gold_matviews/`](../specs/019_gold_matviews/) (requirements, design, tasks).
- **Estado:** T1–T30 completadas. `ruff check`, `ruff format --check`, `pytest` y `./init.sh` en verde.
- **Migración aplicada:** `bd22327c1d90` (`gold materialized views`, `down_revision = "0fa48964369e"`), head local. `alembic check` sin drift.

## Tasks completadas

Todas las de [`tasks.md`](../specs/019_gold_matviews/tasks.md) (T1–T30), en orden y con test primero (rojo → verde), salvo los ajustes de orden documentados en «Desviaciones».

## Trazabilidad `R<n>` → test

| R | Test(s) |
| --- | --- |
| R1 | `test_gold.py::test_result_by_area_sql_has_no_nullable_join` |
| R2 | `test_gold.py::test_result_by_area_regression_seeded`, `test_gold.py::test_result_by_area_matches_legacy_sql_on_local` |
| R3 | `test_gold.py::test_gold_ddl_functions`, `test_gold.py::test_migration_executes_matview_ddl`, `test_gold.py::test_live_gold_relations_match_models` |
| R4 | `test_gold.py::test_gold_ddl_functions`, `test_gold.py::test_live_gold_matview_indexes` |
| R5 | `test_gold.py::test_gold_ddl_functions`, `test_gold.py::test_live_gold_matview_indexes` |
| R6 | `test_gold.py::test_gold_ddl_functions`, `test_gold.py::test_live_gold_relations_match_models` |
| R7 | `test_gold.py::test_poll_trend_keeps_order_by`, `test_gold.py::test_poll_trend_ordered_by_fieldwork` |
| R8 | `test_gold.py::test_ingest_refreshes_gold_once` (dos elecciones, una sola llamada) |
| R9 | `test_gold.py::test_ingest_skipped_does_not_refresh` |
| R10 | `test_gold.py::test_cli_refresh_gold`, `test_gold.py::test_refresh_gold_updates_matviews` |
| R11 | `test_gold.py::test_cli_refresh_gold`, `test_gold.py::test_refresh_gold_updates_matviews` |
| R12 | `test_gold.py::test_refresh_gold_is_idempotent` |
| R13 | `test_gold.py::test_cli_refresh_gold`, `test_gold.py::test_refresh_gold_concurrently`, `test_gold.py::test_refresh_gold_concurrently_emits_concurrently` |
| R14 | `test_gold.py::test_cli_refresh_gold`, `test_gold.py::test_refresh_gold_concurrently` |
| R15 | `test_gold.py::test_ingest_polls_does_not_refresh` |
| R16 | `test_gold.py::test_models_declare_gold_views` |
| R17 | `test_gold.py::test_env_skips_views_and_matviews`, `test_gold.py::test_alembic_check_has_no_drift` |
| R18 | `test_gold.py::test_drawio_gold_page` |
| R19 | `test_gold.py::test_docs_data_model_gold`, `test_gold.py::test_docs_gold_contract`, `test_gold.py::test_docs_ingesta_and_agents_gold` (bloque de `architecture.md`; marcadores inline corregidos a R19) |
| R20 | `test_gold.py::test_docs_ingesta_and_agents_gold` (incluye que `status.md` no vuelva a decir «seis vistas») |
| R21 | `test_gold.py::test_test_schema_has_gold_matviews`, `test_gold.py::test_live_gold_relations_match_models` |
| R22 | `test_gold.py::test_test_schema_has_gold_matviews`, `test_gold.py::test_live_gold_relations_match_models` |
| R23 | `test_gold.py::test_refresh_gold_updates_matviews`, `test_gold.py::test_refresh_gold_is_idempotent` |
| R24 | `test_gold.py::test_refresh_gold_concurrently` |
| R25 | `test_gold.py::test_migration_executes_matview_ddl`, `test_web_role.py::test_role_has_usage_and_select_on_every_gold_view` |
| R26 | `test_web_role.py::test_role_cannot_write_or_create_in_gold` |
| R27 | `test_gold.py::test_results_contract_under_50ms` |

## Migración

`ingestor/alembic/versions/bd22327c1d90_gold_materialized_views.py`

- `upgrade()`: `DROP VIEW IF EXISTS` de las cuatro → `matview_ddl()` (pobladas, `WITH DATA`) → `index_ddl()` (siete) → `ANALYZE` + `GRANT SELECT ... TO votoscope_web` por matview.
- `downgrade()`: `DROP MATERIALIZED VIEW IF EXISTS` de las cuatro y recreación de las vistas con el SQL anterior **congelado en el fichero** (`_LEGACY_VIEWS`), con su `GRANT SELECT`. `bcd8a7409aec` no se toca.
- `uv run alembic upgrade head`: **45,7 s** (una sola vez; crea y puebla las cuatro matviews con 6,05 M votos).
- `uv run alembic current`: `bd22327c1d90 (head)`. `uv run alembic check`: `No new upgrade operations detected.`
- Ciclo `alembic downgrade -1` → `alembic upgrade head` probado en local: el `downgrade` recrea las cuatro vistas con el SQL congelado (válido) y el `upgrade` vuelve a dejar las cuatro matviews con sus índices; head `bd22327c1d90`.

Estado en local tras migrar: `relkind` `m` para `election_summary` (13 filas), `result_by_area` (881.366), `result_by_station` (6.047.666) y `station_turnout` (708.023); `v` para `poll_flat` y `poll_trend`; los siete índices presentes.

## Tiempos medidos (local, en caliente)

`EXPLAIN (ANALYZE, FORMAT JSON)`, una pasada de calentamiento y la mejor de tres; elección más reciente (`election_id = 1`), datos reales de local (13 generales, 6,05 M votos, 708 k mesas-elección).

| Consulta del contrato | Tiempo |
| --- | --- |
| Portada — `election_summary order by election_date desc limit 1` | 0,014 ms |
| Nacional — `result_by_area` (`election_id`, `level='national'`) | 0,010 ms |
| CCAA — `result_by_area` (`election_id`, `level='community'`) | 0,020 ms |
| Provincia — `result_by_area` (`election_id`, `level='province'`, `community_ine_code`) | 0,014 ms |
| Municipio — `result_by_area` (`election_id`, `level='municipality'`, `province_ine_code`) | 0,037 ms |
| Mesa — `station_turnout` (`election_id`, `polling_station_id`) | 0,004 ms |
| Mesa — `result_by_station` (`election_id`, `polling_station_id`) | 0,006 ms |
| Mesas del municipio — `station_turnout` (`election_id`, `municipality_ine_code`) | 1,360 ms |
| Mesas del municipio — `result_by_station` (`election_id`, `municipality_ine_code`) | 29,395 ms |

Todas por debajo de 50 ms (R27). La de `result_by_station` de un municipio grande (Madrid, `28079`) es la más cara porque devuelve ~15 k filas con `SELECT *`: el índice `(election_id, municipality_ine_code)` se usa, pero el margen es el más estrecho (29/50 ms).

Refresco (mismos datos): `refresh_gold` normal **39,2 s**; `--concurrently` **78,9 s**. Coste de la instantánea, no de la consulta. `uv run ingestor refresh-gold` y `uv run ingestor refresh-gold --concurrently` ejecutados de verdad sobre local: **exit 0** en ambos (R11, R14), y el segundo deja el mismo contenido (R12).

Comparación con la definición anterior (`result_by_area` sobre una elección, oráculo legacy): 19–35 s por elección; la comparación completa de local tarda > 200 s (el `JOIN ... IS NOT DISTINCT FROM` no se puede hashear — el problema que elimina esta feature).

## Desviaciones del spec (con motivo)

1. **`design.md` §2 — SQL de `result_by_area` sin agregación por área.** El SQL del diseño selecciona `v.votes` por fila de `vote` en `area_facts`; sin `sum(...)` + `GROUP BY` el resultado tendría una fila por mesa y partido en cada nivel y rompería el grano del contrato (y R2). Implementado con `sum(v.votes)::bigint` y `GROUP BY` por rama (igual que el CTE antiguo `area_votes`) y los blancos agregados por área en el mismo CTE: mismo grano, mismos valores, 7 `UNION ALL` y sin `JOIN ... IS NOT DISTINCT FROM`. El resto del diseño (ventana `valid_votes`, índices, refresco) se sigue tal cual.
2. **Orden de T12/T21.** `_rows()` refresca las matviews en T12, no en T21: al crear las matviews en `conftest.py`, los tests de comportamiento existentes leían instantáneas vacías. T21 se completó con el renombrado del test live y la validación de tipos.
3. **Accesor del test de R1.** `test_result_by_area_sql_has_no_nullable_join` usaba `view_ddl()` (la única API en T1) y pasa a `matview_ddl()` en T4, cuando el SQL se mueve de diccionario.
4. **`test_migration_executes_matview_ddl`.** Comprueba `DROP VIEW IF EXISTS gold.` y la referencia a `MATVIEWS` (la migración itera `MATVIEWS`, no escribe los cuatro nombres); el conjunto exacto de matviews lo fija `test_gold_ddl_functions`.
5. **Test live de regresión (R2) acotado a la elección más reciente.** La comparación fila a fila completa de local tarda > 200 s (el join nulable del oráculo no se puede hashear). El test compara la elección más reciente completa (filas y valores, `EXCEPT` en ambos sentidos) y `test_result_by_area_regression_seeded` cubre los cuatro niveles de forma determinista en CI. Documentado en el docstring del test.
6. **`test_alembic_check_has_no_drift`** ejecuta `python -m alembic check` en un subproceso: importar `alembic.env` en el proceso de pytest ejecuta `fileConfig`, que desactivaría los loggers que usan los tests con `caplog`.
7. **`.agents/status.md`.** El «Pendiente» decía que la 19 estaba pendiente; ahora recoge la 19 como hecha y deja la 20 (`poll_source_drift`) como siguiente.

## Cambios tras la review (ronda 1, CHANGES_REQUESTED)

1. **R13 — `CONCURRENTLY` de verdad.** Nuevo `test_refresh_gold_concurrently_emits_concurrently`: con una sesión falsa que registra las sentencias, exige `REFRESH MATERIALIZED VIEW CONCURRENTLY gold.<name>` y `ANALYZE gold.<name>` para las cuatro de `MATVIEWS`, que no haya refresco plano, `isolation_level = AUTOCOMMIT` y ningún `commit()`. `test_refresh_gold_concurrently` comprueba además datos nuevos en una segunda matview (`station_turnout`: `candidature_votes`/`valid_votes`/`voters` pasan de 0 a 7).
2. **R8 — «fuera del bucle».** `test_ingest_refreshes_gold_once` ingiere ahora **dos** elecciones (`02200806` + `02201905`, helper `_copy_elections`) y exige `len(calls) == 1` con dos `silver.election`; un refresco por elección daría dos llamadas. `test_ingest_skipped_does_not_refresh` usa las mismas dos.
3. **R20 — `status.md`.** `Actualizado: 2026-11-02`; el bullet de la feature 15 ya no dice «seis vistas de solo lectura» (habla de las seis relaciones, cuatro materializadas y dos vistas desde la 19). `test_docs_ingesta_and_agents_gold` falla si vuelve la cadena «seis vistas».
4. **Trazabilidad inline.** `test_drawio_gold_page` → `# R18`, `test_docs_gold_contract` → `# R19`, `test_docs_data_model_gold` → `# R19`, `test_docs_ingesta_and_agents_gold` → `# R19, R20`; docstring del módulo actualizado (cuatro matviews + índices + dos vistas, sin «six views»). Los marcadores de los tests que esta feature no toca siguen con la numeración de la feature 15 (pre-existentes).

Verificación tras la review: `ruff check` y `ruff format --check` limpios, `pytest` **307 passed**, `./init.sh` exit 0 con `alembic check` sin drift.

## Tests skipped

Ninguno en esta sesión (Postgres local levantado y datos cargados): los live (`test_alembic_check_has_no_drift`, `test_live_gold_relations_match_models`, `test_live_gold_matview_indexes`, `test_result_by_area_matches_legacy_sql_on_local`, `test_results_contract_under_50ms`, `test_web_role.py`) corrieron de verdad. Sin base o sin datos se saltan, como el resto de live del repo.

## Ficheros tocados

- `ingestor/src/ingestor/gold.py` (matviews, índices, `refresh_gold`), `models.py` (`info["matview"]`), `cli.py` (`refresh-gold`, refresco al final de `ingest`), `alembic/env.py`, `alembic/versions/bd22327c1d90_gold_materialized_views.py`.
- `ingestor/tests/conftest.py`, `tests/test_gold.py`, `tests/test_web_role.py`.
- `docs/db/schema.drawio` (página Gold), `docs/db/gold.md`, `docs/ingestor/ingesta.md`, `ingestor/AGENTS.md`, `.agents/data-model.md`, `.agents/architecture.md`, `.agents/status.md`.
- `specs/019_gold_matviews/tasks.md` (checkboxes), `progress/current.md`, este fichero.

Sin dependencias nuevas. Sin cambios en `web/` (los tests del rol siguen en `ingestor/tests/`).
