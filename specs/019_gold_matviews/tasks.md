# Tareas — `gold_matviews`

Orden TDD: cada cambio de comportamiento tiene primero su test (rojo) y
después la implementación. El `implementer` marca `[x]` al completar y anota
la trazabilidad `R<n>` → test en `progress/impl_gold_matviews.md`.

## DDL y reescritura de `result_by_area`

- [x] T1 — Añadir en `ingestor/tests/test_gold.py` el test hermético
      `test_result_by_area_sql_has_no_nullable_join`: el SQL de la matview no
      contiene `IS NOT DISTINCT FROM` ni `area_blank`, `blank_votes` aparece en
      el CTE de hechos y hay 7 `UNION ALL` (cuatro niveles de votos + cuatro de
      blancos). Cubre: R1.
- [x] T2 — Reescribir `result_by_area` en `ingestor/src/ingestor/gold.py` con
      un único CTE `area_facts` (votos + blancos) y la ventana de área de
      `design.md` §2. Cubre: R1.
- [x] T3 — Añadir `test_gold_ddl_functions` en `test_gold.py` (sustituye a
      `test_view_ddl_is_single_source`): `view_ddl()` devuelve solo `poll_flat`
      y `poll_trend` con `CREATE VIEW`; `matview_ddl()` devuelve las cuatro con
      `CREATE MATERIALIZED VIEW`; `index_ddl()` devuelve los siete índices; las
      tres respetan la parametrización de esquema. Cubre: R3, R4, R5, R6.
- [x] T4 — Separar en `gold.py` `MATVIEWS`, `VIEWS`, `matview_ddl()`,
      `index_ddl()` y dejar `view_ddl()` con las dos vistas de sondeos; añadir
      el DDL de los siete índices de `design.md` §3. Cubre: R3, R4, R5, R6.
- [x] T5 — Añadir `test_poll_trend_keeps_order_by` (hermético): el SQL de
      `poll_trend` termina en
      `ORDER BY poll_date, p.id, pt.slug`; el test live existente
      `test_poll_trend_ordered_by_fieldwork` se mantiene. Cubre: R7.

## Modelos, autogenerate y migración

- [x] T6 — Actualizar `test_models_declare_gold_views` en `test_gold.py`: las
      cuatro llevan `info["matview"] is True`, las dos de sondeos
      `info["view"] is True`, sin PK/FK ni índices declarados. Cubre: R16.
- [x] T7 — Cambiar en `ingestor/src/ingestor/models.py` las cuatro `Table` de
      resultados a `info={"matview": True}` y actualizar el comentario de la
      sección `gold`. Cubre: R16.
- [x] T8 — Añadir `test_env_skips_views_and_matviews` (hermético: el
      `include_object` menciona `matview` además de `view`) y
      `test_alembic_check_has_no_drift` (live con `alembic.command.check`,
      skip sin base). Cubre: R17.
- [x] T9 — Ampliar `include_object` en `alembic/env.py` para excluir también
      `info["matview"]`. Cubre: R17.
- [x] T10 — Añadir `test_migration_executes_matview_ddl` (hermético): existe
      una única migración `*_gold_materialized_views.py`, importa
      `matview_ddl` e `index_ddl`, hace `DROP VIEW IF EXISTS` de las cuatro y
      no contiene `CREATE MATERIALIZED VIEW` inline. Cubre: R3, R4, R5, R25.
- [x] T11 — Crear
      `ingestor/alembic/versions/<rev>_gold_materialized_views.py` con
      `down_revision = "0fa48964369e"`: drop de las cuatro vistas,
      `matview_ddl()`, `index_ddl()`, `ANALYZE`, `GRANT SELECT` a
      `votoscope_web` y `downgrade` con las cuatro vistas históricas
      congeladas (design.md §6). Aplicar `uv run alembic upgrade head` y
      comprobar `uv run alembic check`. Cubre: R3, R4, R5, R17, R25.

## Esquemas de test y refresco

- [x] T12 — En `ingestor/tests/conftest.py`: excluir las matviews de
      `BASE_TABLES`, crear `matview_ddl()` + `index_ddl()` + `view_ddl()` en
      `polls_test_gold`; añadir `test_test_schema_has_gold_matviews` en
      `test_gold.py` (relkind `m`/`v`, columnas, índices). Cubre: R21, R22.
- [x] T13 — Añadir `test_refresh_gold_updates_matviews` y
      `test_refresh_gold_is_idempotent`: sembrar hechos, refrescar el esquema
      de test, comprobar datos nuevos; segunda ejecución deja el mismo
      contenido. Cubre: R10, R11, R12, R23.
- [x] T14 — Implementar `refresh_gold(session_factory, concurrently=False,
      gold_schema="gold")` en `gold.py` (transacción única en modo normal,
      `AUTOCOMMIT` en concurrente, `ANALYZE` tras cada refresco). Cubre: R10,
      R11, R12, R23.
- [x] T15 — Añadir `test_refresh_gold_concurrently`: con los índices únicos
      del esquema de test, `refresh_gold(..., concurrently=True)` refleja los
      datos nuevos. Cubre: R13, R14, R24.
- [x] T16 — Añadir `test_cli_refresh_gold` (monkeypatch de
      `ingestor.cli.refresh_gold`): `main(["refresh-gold"])` y
      `main(["refresh-gold", "--concurrently"])` salen con 0 y pasan
      `concurrently` correcto. Cubre: R10, R11, R13, R14.
- [x] T17 — Registrar el subcomando `refresh-gold [--concurrently]` en
      `ingestor/src/ingestor/cli.py`. Cubre: R10, R11, R13, R14.

## Refresco al final de `ingest`

- [x] T18 — Añadir `test_ingest_refreshes_gold_once` y
      `test_ingest_skipped_does_not_refresh` con el patrón `_use_cli` de
      `test_polls_load.py` y los fixtures `party_reload`: una ejecución con
      elecciones procesadas llama a `refresh_gold` exactamente una vez; una
      segunda ejecución `skipped` no lo llama. Cubre: R8, R9.
- [x] T19 — En `cli.py`, tras `ingest_path` y dentro del `try`, llamar a
      `refresh_gold(SessionLocal)` una sola vez si
      `any(outcome.status == "processed")`. Cubre: R8, R9.
- [x] T20 — Añadir `test_ingest_polls_does_not_refresh`: con un snapshot de
      `fixtures/wikipedia_polls/`, `main(["ingest-polls", …])` no llama a
      `refresh_gold`. Cubre: R15.

## Tests live y contrato

- [x] T21 — Actualizar `_rows()` para refrescar las matviews del esquema de
      test antes de consultarlas, y `test_live_gold_views_match_models` →
      `test_live_gold_relations_match_models` (une `get_view_names` +
      `get_materialized_view_names`, valida columnas y tipos). Cubre: R3, R6,
      R21, R22.
- [x] T22 — Añadir `test_live_gold_matview_indexes`: los siete índices existen
      en `gold`, y cada matview tiene al menos un índice único. Cubre: R4, R5.
- [x] T23 — Añadir `test_result_by_area_regression_seeded` (fixture sembrado,
      valores exactos por nivel) y
      `test_result_by_area_matches_legacy_sql_on_local` (oráculo con el SQL
      anterior de `area_blank` + `IS NOT DISTINCT FROM`, comparación fila a
      fila; skip sin datos). Cubre: R2.
- [x] T24 — Actualizar `test_web_role.py`: `relkind IN ('v','m')` en la
      comprobación de `SELECT` y en la de escritura; comprobar explícitamente
      `SELECT` sobre las cuatro matviews. Cubre: R25, R26.
- [x] T25 — Añadir `test_results_contract_under_50ms` (live, skip sin datos):
      `EXPLAIN (ANALYZE, FORMAT JSON)` sobre las consultas de resultados del
      contrato, calentamiento + mejor de tres, todas por debajo de 50 ms.
      Cubre: R27.

## Documentación y ERD

- [x] T26 — Actualizar la página Gold de `docs/db/schema.drawio` (título y nota
      `g_matviews_note` con matviews, índices y `refresh-gold`) y ampliar
      `test_drawio_gold_page` con el token «materializada» y la nota. Cubre:
      R18.
- [x] T27 — Actualizar `.agents/data-model.md` §`gold` (cuatro matviews + dos
      vistas, índices, refresco) y ampliar `test_docs_data_model_gold`. Cubre:
      R19.
- [x] T28 — Actualizar `.agents/architecture.md` (seis vistas → matviews +
      vistas; flujo y refresco) y `docs/db/gold.md` (tipo por relación, sección
      «Refresco»); ampliar `test_docs_gold_contract` y el test de arquitectura.
      Cubre: R19.
- [x] T29 — Actualizar `docs/ingestor/ingesta.md` (comando `refresh-gold` y
      refresco al final de `ingest`), `ingestor/AGENTS.md` (funciones de
      `gold.py`, comandos y migración) y `.agents/status.md`; ampliar
      `test_docs_ingesta_and_agents_gold`. Cubre: R20.

## Verificación final

- [x] T30 — Ejecutar `uv run alembic upgrade head`, `uv run alembic check`,
      `uv run pytest` y `./init.sh` en verde; medir en caliente las consultas
      de resultados sobre los datos de local y anotar los tiempos (<50 ms) y la
      trazabilidad `R<n>` → test en `progress/impl_gold_matviews.md`. Cubre:
      R17, R27.
