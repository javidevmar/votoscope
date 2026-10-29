# Esquema gold: vistas y contrato con la web

`gold` contiene solo vistas de solo lectura; la web las consulta en servidor
(Server Components) y **no agrega hechos**: los totales y porcentajes vienen
calculados por las vistas. Nunca se leen tablas `silver` desde la web, y la
web no redefine columnas ni semántica: si falta un dato para una pantalla, se
añade una vista en el ingestador (nueva migración + ERD + este documento).

Las vistas se crean con `uv run alembic upgrade head`; su SQL vive en
`ingestor/src/ingestor/gold.py` (`view_ddl()`), nunca a mano. El rol de
Postgres de solo lectura de la web se crea en la feature 16.

## Vistas

| Vista | Grano | Consulta |
| --- | --- | --- |
| `election_summary` | una fila por elección, con sus totales | hechos agregados (censo, nulos, blancos, candidaturas, válidos, votantes, participación) |
| `result_by_area` | una fila por (elección, nivel, área, partido) | resultados agregados por nación, CCAA, provincia o municipio |
| `result_by_station` | una fila por (elección, mesa, partido) | votos y porcentaje de cada partido en una mesa |
| `station_turnout` | una fila por (elección, mesa) | censo, nulos, blancos, válidos, votantes y participación de la mesa |
| `poll_flat` | una fila por (sondeo, partido) | tabla plana de sondeos: encuestadora, fechas, muestra, %, escaños |
| `poll_trend` | una fila por (sondeo, partido), ordenada por trabajo de campo | serie temporal para el gráfico de tendencia |

Columnas exactas, tipos y nullabilidad: `ingestor/src/ingestor/models.py`
(sección `gold`) y la página «Gold» de [`schema.drawio`](schema.drawio).

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

1. `uv run alembic upgrade head` — crea el esquema `gold` y sus seis vistas
   (idempotente con el resto de migraciones).
2. La web consulta `gold.*` con `SELECT` en servidor, con un rol de solo
   lectura. Nunca escribe, nunca lee `silver`, nunca mueve credenciales al
   cliente.
3. `uv run alembic check` no detecta drift de tablas; los tests del ingestador
   comparan las columnas de las vistas desplegadas con `models.py` y ejercitan
   el SQL en esquemas de test.
