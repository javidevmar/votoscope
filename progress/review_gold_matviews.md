# Review — feature 19 `gold_matviews`

**Veredicto:** APPROVED

Rama `feature/gold_matviews`, cambios sin commitear. Primera pasada: CHANGES_REQUESTED (4 cambios). Segunda pasada: los 4 cambios están aplicados y verificados, sin regresiones.

## Segunda pasada — cambios requeridos

1. **R13 — [x] `CONCURRENTLY` verificado de verdad.** `test_refresh_gold_concurrently_emits_concurrently` (`ingestor/tests/test_gold.py:769-785`) usa una sesión falsa que registra las sentencias: comprueba `REFRESH MATERIALIZED VIEW CONCURRENTLY` y `ANALYZE` para las cuatro `MATVIEWS`, `isolation_level=AUTOCOMMIT`, ningún refresco plano y cero commits. Además, `test_refresh_gold_concurrently` (`:717-734`) comprueba datos nuevos en dos matviews (`result_by_area` y `station_turnout`).
2. **R8 — [x] «fuera del bucle» verificado.** `test_ingest_refreshes_gold_once` (`:1451-1463`) ingiere dos elecciones (`02200806` + `02201905`, `_copy_elections` `:1432-1437`), comprueba que hay dos `Election` cargadas y que `refresh_gold` se llama **una** vez. `test_ingest_skipped_does_not_refresh` (`:1466-1477`) también usa las dos elecciones.
3. **R20 — [x] `.agents/status.md` al día.** `:3` fecha `2026-11-02`; `:14` ya no afirma «seis vistas»: dice «las seis relaciones ... desde la feature 19, las cuatro de resultados son vistas materializadas y las dos de sondeos siguen siendo vistas». `test_docs_ingesta_and_agents_gold` (`test_gold.py:2014-2018`) añade `assert "seis vistas" not in status.lower()`.
4. **Trazabilidad inline — [x].** Marcadores actualizados: `test_drawio_gold_page` `# R18` (`:1835`), `test_docs_gold_contract` `# R19` (`:1900`), `test_docs_data_model_gold` `# R19` (`:1958`), `test_docs_ingesta_and_agents_gold` `# R19, R20` (`:1983`). El docstring del módulo (`:1-8`) ya describe `matview_ddl()`/`index_ddl()`/`view_ddl()`. No quedan referencias a `_copy_election`.

## Verificación independiente (segunda pasada)

- `uv run ruff check .`: `All checks passed!`
- `uv run ruff format --check .`: `49 files already formatted`
- `uv run pytest -q`: **307 passed in 33.32s** (antes 306; +1 test nuevo), sin skips.
- `./init.sh`: **exit 0**; `alembic check` = `No new upgrade operations detected.` (sin drift).
- Tests específicos de los cambios: 5 passed (`test_refresh_gold_concurrently_emits_concurrently`, `test_refresh_gold_concurrently`, `test_ingest_refreshes_gold_once`, `test_ingest_skipped_does_not_refresh`, `test_docs_ingesta_and_agents_gold`).
- Sin regresiones: el diff de la segunda pasada solo toca `.agents/status.md` y `ingestor/tests/test_gold.py`; `gold.py`, CLI, modelos, migración y `conftest.py` no cambian respecto de la primera pasada.
- Migración: verificada en la primera pasada con `alembic downgrade -1` → `0fa48964369e` (cuatro vistas, `relkind='v'`) y `alembic upgrade head` → `bd22327c1d90` (cuatro matviews, siete índices, `relkind='m'`); el fichero de migración no cambió en esta pasada.

## Trazabilidad requirements ↔ tests

- R1: [x] `test_result_by_area_sql_has_no_nullable_join` (`test_gold.py:382-392`).
- R2: [x] `test_result_by_area_regression_seeded` (`:1714-1734`) y `test_result_by_area_matches_legacy_sql_on_local` (`:1735-1801`; oráculo legacy, última elección, alcance documentado en `progress/impl_gold_matviews.md:84`).
- R3: [x] `test_gold_ddl_functions` (`:314-379`), `test_migration_executes_matview_ddl` (`:413-427`) y `test_live_gold_relations_match_models` (`:1180-1219`).
- R4: [x] `test_gold_ddl_functions` (siete índices) y `test_live_gold_matview_indexes` (`:1220-1280`).
- R5: [x] mismo par (índice único por matview).
- R6: [x] `test_gold_ddl_functions` (`view_ddl()` solo dos) y `test_live_gold_relations_match_models` (`get_view_names` = `poll_flat`/`poll_trend`).
- R7: [x] `test_poll_trend_keeps_order_by` (`:395-399`) + `test_poll_trend_ordered_by_fieldwork` (`:1117-1143`).
- R8: [x] `test_ingest_refreshes_gold_once` (`:1451-1463`, dos elecciones, una llamada).
- R9: [x] `test_ingest_skipped_does_not_refresh` (`:1466-1477`).
- R10: [x] `test_cli_refresh_gold` (`:1407-1418`) + `test_refresh_gold_updates_matviews` (`:679-692`).
- R11: [x] `test_cli_refresh_gold` (return 0) + refresco real medido en `progress/impl_gold_matviews.md:74`.
- R12: [x] `test_refresh_gold_is_idempotent` (`:695-702`).
- R13: [x] `test_refresh_gold_concurrently_emits_concurrently` (`:769-785`) + `test_cli_refresh_gold` (pasa el flag) + `test_refresh_gold_concurrently` (`:717-734`).
- R14: [x] `test_cli_refresh_gold` (return 0 con `--concurrently`).
- R15: [x] `test_ingest_polls_does_not_refresh` (`:1480-1492`).
- R16: [x] `test_models_declare_gold_views` (`:256-269`).
- R17: [x] `test_env_skips_views_and_matviews` (`:430-433`) + `test_alembic_check_has_no_drift` (`:436-446`).
- R18: [x] `test_drawio_gold_page` (`:1835-1890`; título y nota `g_matviews_note`).
- R19: [x] `test_docs_data_model_gold` (`:1958-1981`), `test_docs_gold_contract` (`:1900-1939`) y bloque de `architecture.md` en `test_docs_ingesta_and_agents_gold` (`:2020-2025`).
- R20: [x] `test_docs_ingesta_and_agents_gold` (`:1983-2018`; incluye la ausencia de «seis vistas» en `status.md`).
- R21: [x] `test_test_schema_has_gold_matviews` (`:594-637`; `schema != "gold"`).
- R22: [x] `test_test_schema_has_gold_matviews` (columnas) + `test_live_gold_relations_match_models` (tipos).
- R23: [x] `test_refresh_gold_updates_matviews` (`:679-692`).
- R24: [x] `test_refresh_gold_concurrently` (`:717-734`; dos matviews con datos nuevos).
- R25: [x] `test_migration_executes_matview_ddl` (grant) + `test_web_role.py:100-132`.
- R26: [x] `test_web_role.py:172-187`.
- R27: [x] `test_results_contract_under_50ms` (`:1544-1602`; live, calentamiento + mejor de tres).

## Tasks completas

- T1–T30: [x] — todas las de `specs/019_gold_matviews/tasks.md`; sin `[ ]` ni tasks añadidas sin justificar. Desviaciones documentadas en `progress/impl_gold_matviews.md:78-86`.

## Checkpoints

- C1: [x] — piezas base y los 4 agentes; `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#19); `progress/current.md` describe la sesión.
- C3: [x] — ERD ↔ `models.py` ↔ migración `bd22327c1d90`, `alembic check` sin drift; sin DDL a mano; sin dependencias nuevas; logging intacto; sin `print()` ni TODOs en el diff.
- C4: [x] en local — 307 pytest verdes, `ruff check`/`ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para la rama (cambios sin commitear, por diseño del flujo).
- C5: [ ] pendiente del cierre — sin temporales ni basura en `git status` (solo la migración, `specs/019_gold_matviews/`, `progress/impl_gold_matviews.md` y este review sin trackear, esperados); `progress/history.md` con la última sesión (18); feature 19 en `in_progress` (correcto); commits pendientes del OK del usuario.
- C6: [x] — `specs/019_gold_matviews/` con los 3 archivos; EARS con ids estables y tabla acceptance↔R; T1–T30 `[x]`; mapa R↔test en `progress/impl_gold_matviews.md` y marcadores inline actualizados.

## Observaciones no bloqueantes

- Downgrade de la cadena completa: `bd22327c1d90.downgrade()` recrea las cuatro vistas legacy, pero `bcd8a7409aec.downgrade()` itera el `view_ddl()` actual (solo dos vistas de sondeos) y su `DROP SCHEMA IF EXISTS gold` fallaría con las cuatro vistas restantes. El `downgrade -1` de la migración nueva es correcto (verificado) y el design prohíbe editar `bcd8a7409aec`; si se quiere soportar el downgrade completo, decidirlo en spec (p. ej., congelar los cuatro nombres en el downgrade viejo).
