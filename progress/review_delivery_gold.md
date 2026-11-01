# Review — feature 15 `delivery_gold`

**Veredicto:** APPROVED

Feature 15 completa: R1–R22 con verificación real, T1–T24 en `[x]`, `./init.sh` en 0 y los
cuatro hallazgos accionables de la review anterior corregidos de forma comprobable. Los
cambios de alcance de las features 16–18 que conviven en el working tree se tratan como
**fuera de alcance** por decisión vinculante del usuario (specs 016–018, textos BFF de
`web/AGENTS.md`/`.agents/architecture.md`, `feature_list.json` y notas de
`progress/current.md` se quedan en esta rama); no se revisan ni bloquean aquí.

## Verificación independiente

- `./init.sh` re-ejecutado dos veces (antes y después de las mutaciones): **exit 0**, 224
  tests, `ruff check`, `ruff format --check` y `alembic check` («No new upgrade operations
  detected»).
- `ingestor/tests/test_gold.py`: **29/29 passed, 0 skipped**. Los tests live
  (`test_live_gold_views_match_models`, `test_live_poll_brands_colored`) se ejecutan de
  verdad contra el `gold` migrado y los sondeos cargados, no se saltan.
- Los cuatro fixes se han validado con **mutaciones temporales** (código roto a propósito,
  test ejecutado, fichero restaurado y hash comprobado):
  1. **R10, desempate**: quitar `, pt.slug` del `ORDER BY` de `poll_trend` hace fallar
     `test_poll_trend_ordered_by_fieldwork` con `['psoe','psoe','pp','pp']` frente a
     `['psoe','pp','psoe','pp']` (`test_gold.py:805`): el fixture inserta `psoe` antes que
     `pp` en el mismo sondeo/fecha, así que el orden esperado solo se cumple por el
     desempate por `party_slug`.
  2. **R10, cláusula completa**: cambiar `pt.slug` por `pt.name` deja el mismo orden de
     filas del fixture pero rompe la aserción sobre `pg_get_viewdef`
     (`test_gold.py:815-817`). La comprobación del SQL completo no es vacua.
  3. **R8, nombres de geografía**: sustituir en `station_turnout` `c.name AS
     community_name` por `p.name` hace fallar `test_station_turnout_derived_voters` con
     `'Almería' != 'Andalucía'` (`test_gold.py:635`). Los asserts de
     `municipality_name`/`province_name`/`community_name` (`:631-635`, `:647-649`) son
     reales.
  4. **R22, color contra catálogo**: cambiar el color de `pp` en `party_catalog.toml` a
     `#000000` hace fallar `test_live_poll_brands_colored` con
     `assert '#1d84ce' == '#000000'` (`test_gold.py:979`). Ya no basta con «no nulo»:
     compara cada marca con su ficha de `load_catalog()`.
  - Tras cada mutación se restauró el fichero y se comprobó `sha256` idéntico al original;
    `git status`/`git diff --stat` quedan exactamente como estaban. `init.sh` verde de nuevo.
- **Fix de documentación**: `docs/ingestor/ingesta.md:1-3` ya dice «carga en `silver` y
  `gold`» y describe el esquema `gold`; `.agents/architecture.md:45` y
  `ingestor/AGENTS.md:9,16` alinean la descripción con la carga en ambos esquemas. Sin
  rastro de «más adelante» ni de la limitación a `silver`.
- **Informe**: `progress/impl_delivery_gold.md` refleja el working tree real (§Alcance,
  líneas 7–12) y documenta los fixes de la 2.ª pasada (líneas 165–190).

## Trazabilidad requirements ↔ tests

- R1: [x] `test_models_declare_gold_views`, `test_gold_view_types`, `test_live_gold_views_match_models`.
- R2: [x] `test_view_ddl_is_single_source`, `test_migration_executes_view_ddl`.
- R3: [x] migración `bcd8a7409aec` + `uv run alembic upgrade head` (aplicada, head actual) + `test_migration_executes_view_ddl` + `test_live_gold_views_match_models`.
- R4: [x] comando `uv run alembic check` (init.sh §5): «No new upgrade operations detected», como fija la nota de verificación del spec.
- R5: [x] `test_election_summary_aggregates`.
- R6: [x] `test_result_by_area_grain_and_levels`, `test_result_by_area_pct_over_valid_votes`.
- R7: [x] `test_result_by_station_identity_and_pct`.
- R8: [x] `test_station_turnout_derived_voters` (identidad, códigos y **nombres** de municipio/provincia/CCAA, votantes y participación; mutación comprobada).
- R9: [x] `test_poll_flat_shape_and_nulls`.
- R10: [x] `test_poll_trend_ordered_by_fieldwork` (`poll_date` = fin o inicio, orden y desempate reales, `ORDER BY` completo en `pg_get_viewdef`; dos mutaciones comprobadas).
- R11: [x] `test_election_summary_aggregates`, `test_result_by_area_pct_over_valid_votes`, `test_station_turnout_derived_voters`.
- R12: [x] `test_silver_metadata_has_no_new_aggregates` (conjunto cerrado de tablas/columnas de `bronze`/`silver`).
- R13: [x] `test_docs_gold_contract` (seis vistas, tabla pantalla ↔ vista ↔ filtro, semántica, «no agrega», solo lectura).
- R14: [x] `test_docs_environment_topology` (local, Vercel, Neon, GitHub Actions, sin staging).
- R15: [x] `test_drawio_gold_page` + `test_polls_model.py::test_drawio_has_a_page_per_schema_and_domain`.
- R16: [x] `test_docs_data_model_gold` + `test_polls_model.py::test_data_model_documents_page_per_schema_and_domain`.
- R17: [x] `test_docs_ingesta_and_agents_gold` (`ingesta.md`, `ingestor/AGENTS.md`, `architecture.md`, puntero en `web/AGENTS.md`).
- R18: [x] `test_catalog_parses_color`.
- R19: [x] `test_catalog_rejects_invalid_color` (siete variantes inválidas; `IngestError` con la ficha y la ruta).
- R20: [x] `test_resolver_applies_color` (fila existente recoloreada, fila creada con color, ficha sin color deja el valor previo).
- R21: [x] `test_catalog_poll_labels_have_colors` (15 etiquetas → fichas con color válido).
- R22: [x] `test_live_poll_brands_colored` (cada marca con `poll_result` existe en el catálogo y su color **es el de la ficha**; las 15 etiquetas presentes; mutación comprobada) + recarga real documentada en `progress/impl_delivery_gold.md` §Evidencias.

## Tasks completas

`specs/015_delivery_gold/tasks.md:5-28`: **T1–T24 todas `[x]`**, sin `[ ]` ni justificaciones pendientes.

## Checkpoints

- C1: [x] piezas base y los cuatro agentes presentes; `./init.sh` exit 0.
- C2: [x] una sola feature `in_progress` (15; 16–18 en `spec_ready` por decisión del usuario); 224 tests verdes; `progress/current.md` describe la sesión activa.
- C3: [x] ERD (página «Gold») ↔ `models.py` (seis `Table` `info={"view": True}`) ↔ migración `bcd8a7409aec` que ejecuta `view_ddl()`; `alembic check` sin drift; sin DDL a mano ni migraciones editadas; sin dependencias nuevas; sin `print()`/TODO.
- C4: [x] `pytest`, `ruff check`, `ruff format --check` y `alembic check` verdes en local. CI: no verificable aún porque la rama no se ha pusheado (por diseño); ver hallazgo no bloqueante 2.
- C5: [x] sin basura ni temporales (`__pycache__` ignorado); 15 sigue `in_progress`, que es su estado correcto hasta el OK del usuario; commits pendientes de ese OK (puerta del flujo, no de esta review). `specs/018_source_norm/` sigue sin trackear por la decisión vinculante de mantener 16–18 en la rama.
- C6: [x] `specs/015_delivery_gold/` con `requirements.md`, `design.md` y `tasks.md`; EARS estricto; tasks `[x]`; R1–R22 cubiertos (R4 por comando, como fija el spec).

## Cambios requeridos (si aplica)

Ninguno. No queda ningún bloqueo propio de la feature 15.

## Hallazgos no bloqueantes (deuda fuera del alcance de la 15)

1. `.agents/status.md:10,13,21` sigue describiendo `gold` como vacío y los specs 12–14 como «listos para aprobar»; lo cubre la feature 17.
2. `.github/workflows/ingestor.yml` ejecuta `pytest` antes de `alembic upgrade head`, así que los tests live de `gold` se saltarían en CI (patrón previo a esta feature). R3/R4 sí se ejecutan por comando; R22 queda sin cobertura live en CI.
3. La página «Gold» del ERD usa la columna de constraints para `NULL`/`NOT NULL` en vez de vaciarla; cosmético, el test solo rechaza PK/FK.
4. Los cambios de 16–18 permanecen en el working tree por decisión del usuario; no forman parte de este veredicto.
