# Requisitos — `delivery_gold`

Feature `id 15` de [`feature_list.json`](../../feature_list.json). Alcance: el esquema `gold` —vistas de resultados electorales y de sondeos, con el contrato que consumirá `web/`—, la topología de entornos y la sincronización ERD ↔ `models.py` ↔ migración. No toca `web/` (feature 16), no cambia `silver` (salvo `party.color`, ver R18–R22) y no añade dependencias.

La cola ejecuta antes las features 12–14 (`party-norm`): cuando esta feature se implemente, `silver.party` ya tiene la identidad curada por el catálogo y el resolver compartido de [`specs/012_party_catalog/`](../012_party_catalog/design.md) y [`specs/014_party_polls/`](../014_party_polls/design.md). El frontend (feature 16) consumirá estas vistas **sin redefinir el contrato**: todo lo que la web muestra viene calculado desde aquí.

## R1

El sistema DEBE declarar las seis vistas de `gold` —`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat` y `poll_trend`— como `Table` de `Base.metadata` en `ingestor/src/ingestor/models.py`, con `schema="gold"` e `info={"view": True}`.

## R2

El sistema DEBE exponer el SQL de las seis vistas en `ingestor/src/ingestor/gold.py` mediante `view_ddl(gold_schema="gold", silver_schema="silver") -> dict[str, str]`, como única fuente de las sentencias `CREATE VIEW` (la migración y los tests la consumen; no hay copias).

## R3

CUANDO se aplica la migración de esta feature con `uv run alembic upgrade head` sobre una base en la revisión anterior, el sistema DEBE crear el esquema `gold` si no existe y las seis vistas con sus columnas.

## R4

CUANDO se ejecuta `uv run alembic check` con la base migrada, el sistema DEBE informar de que no hay operaciones pendientes entre `models.py` y la base (sin drift).

## R5

El sistema DEBE definir `gold.election_summary` con una fila por elección con hechos y las columnas `election_id`, `election_type`, `election_date`, `election_name`, `census`, `null_votes`, `blank_votes`, `candidature_votes`, `valid_votes`, `voters` y `turnout_pct`.

## R6

El sistema DEBE definir `gold.result_by_area` con una fila por (elección, nivel, área, partido), `level` en `national` | `community` | `province` | `municipality`, las columnas de área aplicables al nivel (`community_ine_code`, `community_name`, `province_ine_code`, `province_name`, `municipality_id`, `municipality_ine_code`, `municipality_name`; nulas las del nivel que no aplique) y las columnas del partido (`party_id`, `party_slug`, `party_name`, `party_color`) con `votes` y `pct`.

## R7

El sistema DEBE definir `gold.result_by_station` con una fila por (elección, mesa, partido), la identidad de la mesa (`polling_station_id`, `district`, `section`, `code`), su geografía (`municipality_id`, `municipality_ine_code`, `municipality_name`, `province_ine_code`, `province_name`, `community_ine_code`, `community_name`) y las columnas del partido con `votes` y `pct`.

## R8

El sistema DEBE definir `gold.station_turnout` con una fila por (elección, mesa), la identidad y geografía de la mesa (las mismas columnas de R7 sin el partido) y las columnas `census`, `null_votes`, `blank_votes`, `candidature_votes`, `valid_votes`, `voters` y `turnout_pct`.

## R9

El sistema DEBE definir `gold.poll_flat` con una fila por resultado de sondeo (sondeo × partido) y las columnas `poll_id`, `pollster_id`, `pollster_slug`, `pollster_name`, `source`, `election_type`, `election_id`, `fieldwork_start`, `fieldwork_end`, `sample_size`, `turnout`, `revision_id`, `party_id`, `party_slug`, `party_name`, `party_color`, `pct`, `seats_min` y `seats_max`.

## R10

El sistema DEBE definir `gold.poll_trend` con una fila por resultado de sondeo, la fecha `poll_date` = `coalesce(fieldwork_end, fieldwork_start)` y las columnas `poll_id`, `pollster_slug`, `pollster_name`, `source`, `revision_id`, `election_type`, `election_id`, las del partido, `pct`, `seats_min` y `seats_max`, ordenada por `poll_date` ascendente (nulos al final), después `poll_id` y `party_slug`.

## R11

El sistema DEBE derivar en las vistas `gold` los votos válidos como votos a candidaturas + blancos, los votantes como válidos + nulos, y los porcentajes de resultados (`result_by_area.pct` y `result_by_station.pct`) como votos del partido / votos válidos del área o mesa × 100 redondeados a 2 decimales, nulos si el denominador es 0.

## R12

El sistema NO DEBE añadir a `silver` tablas, columnas ni agregados nuevos (los totales y porcentajes derivados viven solo en las vistas `gold`).

## R13

El sistema DEBE documentar el contrato gold ↔ front en `docs/db/gold.md`, con la tabla pantalla ↔ vista(s) ↔ filtro de cada pantalla del MVP (resultados por mesa y agregados; sondeos planos y tendencia), la semántica de los porcentajes y la regla «la web no agrega hechos».

## R14

El sistema DEBE documentar en `.agents/environment.md` la topología de entornos decidida: local (Postgres de docker-compose, ingestador y web en la máquina) y producción (web en Vercel, Postgres gestionado Neon y el job de sondeos en GitHub Actions), sin entorno de staging.

## R15

El sistema DEBE añadir a `docs/db/schema.drawio` la página «Gold» con las seis vistas como contenedores y sus columnas, sin tocar las páginas existentes.

## R16

El sistema DEBE actualizar `.agents/data-model.md`: la regla de páginas pasa a «(Bronze, Silver, Bronze polls, Silver polls, Gold)», el modelo v2 describe las vistas de `gold` y la curación de `party.color` desde el catálogo.

## R17

El sistema DEBE actualizar `docs/ingestor/ingesta.md` y `ingestor/AGENTS.md` con el esquema `gold` (vistas, semántica y cómo se aplican) y `.agents/architecture.md` con el esquema `gold` ya creado y el contrato, añadiendo en `web/AGENTS.md` el puntero a `docs/db/gold.md`.

## R18

El sistema DEBE admitir una clave opcional `color` (hexadecimal `#rrggbb`) en las fichas de `ingestor/src/ingestor/data/party_catalog.toml`.

## R19

SI una ficha declara un `color` que no es un hexadecimal `#rrggbb` ENTONCES el sistema DEBE abortar la carga del catálogo con `IngestError` y un mensaje que nombre la ficha.

## R20

CUANDO el resolver resuelve una etiqueta, el sistema DEBE dejar `party.color` con el color de la ficha cuando esta lo declare (aplique a una fila creada o ya existente) y con el valor previo de la fila cuando la ficha no lo declare.

## R21

El sistema DEBE declarar `color` en las fichas del catálogo de las 15 etiquetas de sondeos (las del mapeo `PARTY_COLUMNS` sustituido en la feature 14), de modo que la tabla y la tendencia de sondeos tengan color curado.

## R22

CUANDO se recargan las elecciones y los sondeos con el catálogo vigente (`uv run ingestor ingest --force` e `uv run ingestor ingest-polls --force`), el sistema DEBE dejar `silver.party.color` con el color de la ficha en las filas de las marcas cubiertas por el catálogo.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «vistas gold para resultados y sondeos (agregados y porcentajes solo aquí)» | R1, R2, R3, R5, R6, R7, R8, R9, R10, R11, R12 |
| «contrato gold ↔ front documentado (qué vista alimenta qué pantalla)» | R13 |
| «topología de entornos decidida y documentada» | R14 |
| «ERD ↔ modelos ↔ migración para lo que toque el esquema» | R1, R2, R3, R4, R15, R16 |
| Extra: documentación del ingestador y de la arquitectura al día | R17 |
| Extra: curación de `party.color` desde el catálogo (`.agents/data-model.md` la sitúa «al construir `gold`»; las vistas la exponen y la web la consume) | R18, R19, R20, R21, R22 |

## Notas de alcance

- **La web no reimplementa nada**: cada cifra que muestra (votos, %, escaños, participación) viene calculada por las vistas; el contrato (R13) lo deja cerrado para la feature 16. Quedan fuera del MVP los agregados de participación por área (solo hay participación por mesa en `station_turnout`) y el reparto de escaños de las elecciones (la fuente no lo publica como hecho).
- **`level` es vocabulario cerrado**: `national`, `community`, `province`, `municipality`; cada fila lleva solo las columnas de área de su nivel (las demás nulas). La vista de provincia incluye además su CCAA para colorear y para enlazar sin joins.
- **Dos vistas para sondeos, como pide la descripción**: `poll_flat` (plana: encuestadora, partido, %, escaños, fechas, `source`/`revision_id`) para la tabla, y `poll_trend` (ordenada por trabajo de campo) para la tendencia. Los sondeos sin `fieldwork_end` se ordenan por `fieldwork_start`; los de partido sin color o sin porcentaje llegan con `NULL` y la web decide el hueco — la vista no filtra.
- **`gold` son solo vistas**: nada de tablas ni materializaciones; el volumen local (6 M de votos, 13 elecciones) aguanta el cálculo al vuelo en los filtros del front.
- **`party.color`** se cura en el catálogo (una sola fuente de identidad, con diff revisable) y el resolver la materializa en cada recarga; los valores concretos se aprueban en el diff, como los alias de la feature 12. Las fichas sin `color` dejan la fila como esté (`NULL` hoy): la web usa su color por defecto para esas marcas.
- **Sin `web/` en esta feature**: la web solo recibe el contrato; el rol de Postgres de solo lectura y el scaffold son de la feature 16.

## Nota de verificación

- R1, R2, R5–R12: `ingestor/tests/test_gold.py` — metadata sin BD (`test_models_declare_gold_views`, `test_view_ddl_is_single_source`, `test_silver_metadata_has_no_new_aggregates`) y comportamiento con la fixture de esquemas de test (`test_election_summary_aggregates`, `test_result_by_area_grain_and_levels`, `test_result_by_area_pct_over_valid_votes`, `test_result_by_station_identity_and_pct`, `test_station_turnout_derived_voters`, `test_poll_flat_shape_and_nulls`, `test_poll_trend_ordered_by_fieldwork`).
- R3, R4: se verifican por comando — `uv run alembic upgrade head` + `uv run alembic check` (presentes en `init.sh` §5 y en la CI) — y con el test de solo lectura `test_live_gold_views_match_models` (se salta sin Postgres o sin migrar); no se duplican en pytest: la base es el objeto de verificación.
- R13, R14, R16, R17: tests de documentos en `test_gold.py` (`test_docs_gold_contract`, `test_docs_environment_topology`, `test_docs_data_model_gold`, `test_docs_ingesta_and_agents_gold`).
- R15: `test_drawio_gold_page` (parseo XML con la biblioteca estándar) y el ajuste de la tupla de páginas en `ingestor/tests/test_polls_model.py`.
- R18–R21: `test_gold.py` — `test_catalog_parses_color`, `test_catalog_rejects_invalid_color`, `test_resolver_applies_color`, `test_catalog_poll_labels_have_colors`.
- R22: `test_live_poll_brands_colored` (solo lectura; se salta sin Postgres o sin sondeos cargados) y la verificación de la recarga documentada en `progress/impl_delivery_gold.md`.
- R20 aplica también a las filas creadas por el resolver: `test_resolver_applies_color` cubre creación y recoloreo.
