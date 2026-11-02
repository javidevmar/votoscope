# Esquema gold: vistas materializadas, vistas y contrato con la web

`gold` contiene solo relaciones de solo lectura: las cuatro de resultados son
**vistas materializadas** con índices y las dos de sondeos son **vistas**. La
web las consulta en servidor (Server Components) y **no agrega hechos**: los
totales y porcentajes vienen calculados por las relaciones. Nunca se leen
tablas `silver` desde la web, y la web no redefine columnas ni semántica: si
falta un dato para una pantalla, se añade una relación en el ingestador (nueva
migración + ERD + este documento).

Las relaciones se crean con `uv run alembic upgrade head`; su DDL vive en
`ingestor/src/ingestor/gold.py` (`matview_ddl()`, `index_ddl()` y `view_ddl()`),
nunca a mano. El rol de Postgres de solo lectura de la web se crea en la
feature 16.

## Relaciones

| Relación | Tipo | Grano | Consulta |
| --- | --- | --- | --- |
| `election_summary` | materializada | una fila por elección, con sus totales | hechos agregados (censo, nulos, blancos, candidaturas, válidos, votantes, participación) |
| `result_by_area` | materializada | una fila por (elección, nivel, área, partido) | resultados agregados por nación, CCAA, provincia o municipio |
| `result_by_station` | materializada | una fila por (elección, mesa, partido) | votos y porcentaje de cada partido en una mesa |
| `station_turnout` | materializada | una fila por (elección, mesa) | censo, nulos, blancos, válidos, votantes y participación de la mesa |
| `poll_flat` | vista | una fila por (sondeo, partido) | tabla plana de sondeos: encuestadora, fechas, muestra, %, escaños |
| `poll_trend` | vista | una fila por (sondeo, partido), ordenada por trabajo de campo | serie temporal para el gráfico de tendencia |

Columnas exactas, tipos y nullabilidad: `ingestor/src/ingestor/models.py`
(sección `gold`) y la página «Gold» de [`schema.drawio`](schema.drawio).

### Índices

Siete índices, alineados con los filtros del contrato y con el requisito de un
índice único por vista materializada para `REFRESH MATERIALIZED VIEW
CONCURRENTLY`:

| Índice | Relación | Columnas |
| --- | --- | --- |
| `uq_gold_election_summary_election_id` | `election_summary` | `election_id` (único) |
| `uq_gold_result_by_area_grain` | `result_by_area` | `election_id`, `level`, `community_ine_code`, `province_ine_code`, `municipality_id`, `party_id` (único, `NULLS NOT DISTINCT`) |
| `ix_gold_result_by_area_province` | `result_by_area` | `election_id`, `level`, `province_ine_code` |
| `uq_gold_result_by_station_grain` | `result_by_station` | `election_id`, `polling_station_id`, `party_id` (único) |
| `ix_gold_result_by_station_municipality` | `result_by_station` | `election_id`, `municipality_ine_code` |
| `uq_gold_station_turnout_grain` | `station_turnout` | `election_id`, `polling_station_id` (único) |
| `ix_gold_station_turnout_municipality` | `station_turnout` | `election_id`, `municipality_ine_code` |

## Refresco

Las vistas materializadas son instantáneas: los hechos nuevos **no aparecen
hasta el siguiente refresco** (la web puede servir datos obsoletos entre
refrescos; es el precio de responder en milisegundos).

- `uv run ingestor ingest <ruta>` refresca las cuatro **una sola vez al final**,
  y solo si algún fichero quedó `processed`; una ejecución en la que todo se
  salta no refresca nada.
- `uv run ingestor refresh-gold` refresca las cuatro; es idempotente.
- `uv run ingestor refresh-gold --concurrently` usa `REFRESH MATERIALIZED VIEW
  CONCURRENTLY`: no bloquea a los lectores y exige los índices únicos de arriba.
- `uv run ingestor ingest-polls` **no** refresca nada: los sondeos son vistas y
  reflejan `silver` al instante.

## Contrato gold ↔ front

| Pantalla | Vista(s) | Filtro / orden |
| --- | --- | --- |
| Resultados — portada (última general) | `election_summary` | `order by election_date desc limit 1` |
| Resultados — nacional | `result_by_area` | `election_id = … and level = 'national'` |
| Resultados — mapa de CCAA | `result_by_area` | `election_id = … and level = 'community'` |
| Resultados — provincia | `result_by_area` | `election_id = … and level = 'province' and community_ine_code = …` |
| Resultados — municipio | `result_by_area` | `election_id = … and level = 'municipality' and province_ine_code = …` |
| Resultados — mesas del municipio | `station_turnout` + `result_by_station` | `election_id = … and municipality_ine_code = …` |
| Resultados — detalle de mesa | `station_turnout` + `result_by_station` | `election_id = … and polling_station_id = …` |
| Sondeos — tendencia | `poll_trend` | series por `party_slug`, x = `poll_date` (ya ordenada) |
| Sondeos — tabla | `poll_flat` | agrupable por `pollster_slug`; fechas, `pct`, escaños, `source`/`revision_id` |

## Semántica

- **`level`** es vocabulario cerrado: `national`, `community`, `province` o
  `municipality`. Cada fila de `result_by_area` lleva solo las columnas de
  área de su nivel (las demás son `NULL`); la de provincia incluye además su
  CCAA para colorear y enlazar sin joins.
- **Votos válidos** = votos a candidaturas + votos en blanco. **Votantes** =
  válidos + nulos.
- **`pct`** (en `result_by_area` y `result_by_station`) = votos del partido /
  votos válidos del área o mesa × 100, redondeado a 2 decimales; `NULL` si el
  denominador es 0.
- **`turnout_pct`** = votantes / censo × 100, redondeado a 2 decimales; `NULL`
  si el censo es 0.
- **`party_color`** puede ser `NULL` (la web usa su color por defecto para esa
  marca); `municipality_name` también puede ser `NULL` (municipios extintos sin
  nombre en la fuente).
- **Sondeos**: `poll_date` = `coalesce(fieldwork_end, fieldwork_start)`; la
  vista no filtra, así que `pct` y `seats_min`/`seats_max` pueden llegar
  `NULL` (la web deja el hueco en la serie). `source` y `revision_id`
  identifican el snapshot de Wikipedia y alimentan la atribución (feature 17).

## Aplicación y verificación

1. `uv run alembic upgrade head` — crea el esquema `gold` con las cuatro vistas
   materializadas (pobladas, con sus índices) y las dos vistas (idempotente con
   el resto de migraciones).
2. La web consulta `gold.*` con `SELECT` en servidor, con un rol de solo
   lectura. Nunca escribe, nunca lee `silver`, nunca mueve credenciales al
   cliente.
3. `uv run alembic check` no detecta drift de tablas; los tests del ingestador
   comparan las columnas de las relaciones desplegadas con `models.py`,
   comprueban los índices, ejercitan el SQL y el refresco en esquemas de test y
   miden las consultas del contrato.
