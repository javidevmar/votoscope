# Implementación — `delivery_gold` (feature 15)

Rama `feature/delivery-gold` (apilada sobre `feature/party-polls`). Spec:
[`specs/015_delivery_gold/`](../specs/015_delivery_gold/). Cambios en el working
tree, sin commit ni push.

**Alcance del working tree**: por decisión del usuario, esta rama conserva
además los cambios de alcance de las features 16–18 (specs `016`–`018`,
`feature_list.json`, el texto BFF de `web/AGENTS.md` y `.agents/architecture.md`,
y `progress/current.md`). La feature 15 solo aporta en los dos documentos
compartidos el puntero a `docs/db/gold.md` (R17) y el bullet de `gold`; los
textos BFF son de la 16 y no forman parte de este diff.

## Resumen

- Seis vistas de solo lectura en el esquema `gold`, declaradas como `Table` de
  Core (`info={"view": True}`, sin PK/FK) en `models.py`, con el SQL en
  `ingestor/src/ingestor/gold.py` (`view_ddl()`, única fuente) y creadas por la
  migración `bcd8a7409aec_gold_views.py`.
- `alembic/env.py` excluye las vistas del autogenerate (`include_object`);
  `uv run alembic check` no reporta drift.
- Contrato `gold` ↔ front en `docs/db/gold.md`; topología de entornos en
  `.agents/environment.md`; ERD con página «Gold»; documentación del ingestador
  y de la arquitectura al día.
- Curación de `party.color`: clave opcional `color = "#rrggbb"` en el catálogo
  (validada con `IngestError`), aplicada por `PartyResolver` a filas nuevas y
  existentes, y materializada con la recarga real de elecciones y sondeos.
- Sin dependencias nuevas. Sin cambios en `silver` salvo `party.color`.

## Tasks

T1–T24 completadas en orden (marcadas `[x]` en `tasks.md`). Resumen:

| Task | Qué se hizo |
| --- | --- |
| T1 | `tests/test_gold.py`: metadata de las seis vistas, `view_ddl()` y conjunto cerrado de tablas/columnas de `bronze`/`silver`. |
| T2 | `src/ingestor/gold.py` con `_VIEW_SQL` y `view_ddl(gold_schema, silver_schema)`. |
| T3 | Sección `gold` en `src/ingestor/models.py` (seis `Table` de Core). |
| T4 | `include_object` en `alembic/env.py` (online y offline). |
| T5 | Migración `bcd8a7409aec_gold_views.py`: `CREATE SCHEMA IF NOT EXISTS gold` + `op.execute(view_ddl())`; `downgrade` inverso. Test extra `test_migration_executes_view_ddl` (la migración no copia SQL). |
| T6 | `alembic upgrade head` + `alembic check` verdes; `downgrade -1` → `upgrade head` probado (6 objetos en `gold` antes y después). |
| T7 | `conftest.py`: esquema `polls_test_gold`, `create_all`/vaciado solo con tablas no-vista y creación de las vistas con `view_ddl()` parametrizado. `test_polls_load`/`test_polls_run`/`test_party_reload` verdes. |
| T8–T13 | Tests de comportamiento (resumen, áreas, mesas, participación, sondeos planos y tendencia) contra los esquemas de test. |
| T14 | `test_live_gold_views_match_models` (solo lectura, skip sin Postgres/vistas). |
| T15–T17 | `PartyEntry.color` + validación `#rrggbb`; color aplicado por el resolver; 24 fichas del catálogo con color (las 15 de sondeos + 9 marcas principales del 2023). |
| T18 | Recarga real de los 13 procesos y de los sondeos; verificación SQL; `test_live_poll_brands_colored` (ver §Evidencias). |
| T19 | Página «Gold» del ERD (6 contenedores, sin PK/FK), `test_drawio_gold_page` y tupla de páginas actualizada en `test_polls_model.py` y en la regla de `data-model.md`. |
| T20 | `docs/db/gold.md` + `test_docs_gold_contract`. |
| T21 | «Topología de entornos» en `.agents/environment.md` + `test_docs_environment_topology`. |
| T22 | `.agents/data-model.md` (vistas y curación de color) y `.agents/architecture.md` + `test_docs_data_model_gold`. |
| T23 | `docs/ingestor/ingesta.md`, `ingestor/AGENTS.md` y puntero en `web/AGENTS.md` + `test_docs_ingesta_and_agents_gold`. |
| T24 | Puerta final: `./init.sh` verde (ruff, format, pytest, alembic check) y este informe. |

## Trazabilidad R ↔ test

| R | Verificación |
| --- | --- |
| R1 | `test_models_declare_gold_views`, `test_gold_view_types`, `test_live_gold_views_match_models` |
| R2 | `test_view_ddl_is_single_source`, `test_migration_executes_view_ddl` |
| R3 | `test_migration_executes_view_ddl` + `uv run alembic upgrade head` (y round-trip `downgrade`/`upgrade`) + `test_live_gold_views_match_models` |
| R4 | Comando `uv run alembic check` (init.sh §5 y CI); sin duplicar en pytest |
| R5 | `test_election_summary_aggregates`, `test_live_gold_views_match_models` |
| R6 | `test_result_by_area_grain_and_levels`, `test_result_by_area_pct_over_valid_votes` |
| R7 | `test_result_by_station_identity_and_pct` |
| R8 | `test_station_turnout_derived_voters` (identidad y geografía completas: códigos y nombres de municipio, provincia y CCAA; votantes y participación) |
| R9 | `test_poll_flat_shape_and_nulls` |
| R10 | `test_poll_trend_ordered_by_fieldwork` (`poll_date` = fin o inicio; orden completo `poll_date, poll_id, party_slug` en `pg_get_viewdef` y desempate real con dos partidos en la misma fecha insertados en orden inverso) |
| R11 | `test_election_summary_aggregates`, `test_result_by_area_pct_over_valid_votes`, `test_station_turnout_derived_voters` |
| R12 | `test_silver_metadata_has_no_new_aggregates` |
| R13 | `test_docs_gold_contract` |
| R14 | `test_docs_environment_topology` |
| R15 | `test_drawio_gold_page`, `test_polls_model.py::test_drawio_has_a_page_per_schema_and_domain` |
| R16 | `test_docs_data_model_gold`, `test_polls_model.py::test_data_model_documents_page_per_schema_and_domain` |
| R17 | `test_docs_ingesta_and_agents_gold` |
| R18 | `test_catalog_parses_color` |
| R19 | `test_catalog_rejects_invalid_color` |
| R20 | `test_resolver_applies_color` |
| R21 | `test_catalog_poll_labels_have_colors` |
| R22 | `test_live_poll_brands_colored` (cada marca con `poll_result` resuelve a una ficha del catálogo y su `color` es el de la ficha; las 15 etiquetas están presentes) + recarga documentada abajo |

Todos los tests nuevos viven en `ingestor/tests/test_gold.py` (29) salvo la
tupla de páginas de `test_polls_model.py` (2 aserciones actualizadas).

## Evidencias de la recarga (T18, R22)

Entorno: Postgres local `localhost:5434` (proyecto docker `1poller`),
`votoscope/votoscope@votoscope`. Los symlinks `data/raw/*` del worktree
apuntan al checkout principal y el loader compara rutas **resueltas**, así que
se ejecutó con `RAW_DIR` apuntando a la copia real (sin tocar código):

```sh
cd ingestor
RAW_DIR=/Users/javier/Developer/1poller/data/raw \
  uv run ingestor ingest /Users/javier/Developer/1poller/data/raw/congreso --force
# 13 procesos: 02198606 … 02202307 → processed (3:16 min)

RAW_DIR=/Users/javier/Developer/1poller/data/raw \
  uv run ingestor ingest-polls --force
# 3 snapshots → processed; el último, revisión 1380859635 (575 sondeos)
```

Estado tras la recarga:

```
elections=13 votes=6047666 polls=575 poll_results=6125 party=521 party_with_color=24
```

Marca de sondeos sin color (la consulta del design), vacía:

```sql
SELECT p.slug FROM silver.party p
JOIN silver.poll_result pr ON pr.party_id = p.id
WHERE p.color IS NULL GROUP BY 1 ORDER BY 1;
-- (0 rows)
```

Colores materializados (24): `pp #1d84ce`, `psoe #e30713`, `vox #63be21`,
`sumar #e51c55`, `podemos #6b2c91`, `erc #ffb232`, `jxcat-junts #00a2ad`,
`eh-bildu #8fbf2f`, `eaj-pnv #007a33`, `bng #4d9de0`, `cca #f2c200`,
`u-p-n #1f3a93`, `salf #2b2b2b`, `adelante-andalucia #00a651`,
`alianca-cat #1f4e9c` (las 15 de sondeos) más `pacma #00a99d`, `cup-pr #f5c400`,
`fo #1b3a6b`, `nc-bc #f6a800`, `pdecat-e-ciu #0b3d91`,
`recortes-cero #9e1b32`, `pum-j #6a1b9a`, `upl #2e7d32`, `existe #607d8b`.

Quedan 8 marcas del 2023 sin color, todas marginales y fuera de la curación
principal (la web usa su color por defecto): `pcte` (18.218 votos), `gbai`
(9.938), `sy` (9.697), `escanos-en-blanco` (8.448), `jm` (8.293), `xav`
(7.362), `bqex` (5.807), `cj` (5.620).

Comprobación de las vistas contra los anclajes del design (2023):

```
election_date 2023-07-23: census 37.469.141, voters 24.952.653, turnout_pct 66.60
result_by_area national: pp 8.161.117 / 33.06 ; psoe 7.821.777 / 31.68
```

## Desviaciones y notas

1. **`RAW_DIR` en la recarga**: los symlinks de `data/raw` del worktree
   resuelven fuera de `RAW_DIR` y el loader rechaza ficheros «outside the
   bronze directory». Se pasó `RAW_DIR` al checkout real; no hubo cambio de
   código ni del contrato.
2. **`pct` NULL con denominador 0**: en `result_by_area`/`result_by_station`
   una fila solo existe si el partido tiene votos, así que el denominador
   (candidaturas + blancos del área/mesa) nunca es 0 en filas emitidas. El
   test fija la fórmula con datos y comprueba que el `nullif(` sigue en el SQL
   de `view_ddl()`; no se inventó un caso de datos imposible.
3. **Tupla de páginas del ERD en T19**: el design exige actualizar las dos
   aserciones de `test_polls_model.py` junto con la página «Gold», así que la
   frase de la regla en `.agents/data-model.md` se ajustó en T19; el resto de
   R16 (vistas en el modelo v2 y curación de `party.color`) se completó en T22.
4. **Validador del ERD**: el fichero es multi-página y el validador de la
   skill marca `duplicate id 0/1` en cualquier `.drawio` con varias páginas
   (ya ocurría en `HEAD`, comprobado). La página «Gold» se validó aislada:
   **0 errores** y 6 warnings esperados («no PK marker»: las vistas no tienen
   PK por diseño). Se exportó un PNG temporal y se revisó: seis contenedores
   alineados, sin solapes ni texto cortado.
5. **`include_object`** se escribió como `return not (...)` para satisfacer
   `ruff` (SIM103), mismo comportamiento que el snippet del design.
6. **Corrección colateral** en `.agents/architecture.md`: el puerto del
   docker-compose decía 5433 y es 5434 (coherente con `environment.md` y
   `docker-compose.yml`).
7. **Sin dependencias nuevas**; `sqlalchemy`/`alembic` ya estaban aprobadas.

## Revisión del reviewer (2.ª pasada)

Cambios aplicados sobre los hallazgos accionables de la 15
([`review_delivery_gold.md`](review_delivery_gold.md)):

- **Hallazgo 2 (descripción de la documentación)**: `ingestor/AGENTS.md` ya no
  dice «más adelante» ni limita `ingesta.md` a `silver`; el mapa de
  `.agents/architecture.md` también refleja la carga en `silver` y `gold`.
- **Hallazgo 3 (R10)**: `test_poll_trend_ordered_by_fieldwork` fija la cláusula
  completa `order by coalesce(p.fieldwork_end, p.fieldwork_start), p.id,
  pt.slug` sobre `pg_get_viewdef` y el fixture inserta `psoe` antes que `pp` en
  el mismo sondeo/fecha, de modo que el orden esperado (`pp` antes que `psoe`)
  solo se cumple por el desempate `party_slug`, no por el orden de inserción.
- **Hallazgo 4 (R8)**: `test_station_turnout_derived_voters` comprueba
  `municipality_name`, `province_name` y `community_name` (Abla/Olula,
  Almería, Andalucía), además de los códigos.
- **Hallazgo 5 (R22)**: `test_live_poll_brands_colored` compara el `color` de
  cada marca con `load_catalog()` (no solo que no sea nulo) y exige que las 15
  etiquetas de sondeos estén entre las marcas con resultados.
- **Bloqueante de alcance**: no se separan los cambios de 16–18; el usuario
  decide mantenerlos en esta rama. Este informe describe el working tree real y
  acota lo que aporta la 15 en `web/AGENTS.md` y `.agents/architecture.md`
  (puntero de R17 y bullet de `gold`; el texto BFF es de la 16).

Tras los cambios: `pytest` 224 verdes (29 en `test_gold.py`), `ruff check`,
`ruff format --check` y `alembic check` limpios; `./init.sh` en verde.

## Estado final

- `uv run pytest`: 224 tests verdes.
- `uv run ruff check .` y `uv run ruff format --check .`: limpios.
- `uv run alembic check`: «No new upgrade operations detected».
- `./init.sh`: verde.
