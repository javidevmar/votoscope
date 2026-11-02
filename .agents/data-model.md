# Modelo de datos

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Fuente de verdad

- ERD de referencia: **`docs/db/schema.drawio`** (draw.io nativo, editable; una página por esquema y dominio (Bronze, Silver, Bronze polls, Silver polls, Gold)).
- Modelos: **`ingestor/src/ingestor/models.py`** (SQLAlchemy 2).
- Migraciones: **`ingestor/alembic/`** — son la fuente de verdad de la base de datos.
- Esquemas: `bronze` (registro de ingestas), `silver` (hechos normalizados) y `gold` (vistas materializadas y vistas de solo lectura para el frontend).

## Regla de sincronización (obligatoria)

Todo cambio de modelo se refleja siempre en los tres sitios:

1. ERD — `docs/db/schema.drawio`
2. Modelos — `ingestor/src/ingestor/models.py`
3. Una migración — `ingestor/alembic/versions/`

Nunca se escribe DDL a mano ni ficheros SQL de inicialización. Nunca se edita una migración ya aplicada: se crea otra, a no ser que no se haya aplicado en producción.

## Modelo v2 (vigente)

- En inglés; PK natural `ine_code` en `autonomous_community` y `province`; PK sustitutas `id` (serial) en el resto, con códigos naturales únicos aparte.
- `bronze.ingestion`: una fila por fichero fuente (ruta, sha256 único, tamaño, fuente, estado, fecha).
- `silver.autonomous_community` / `province` / `municipality`: geografía con códigos INE (municipio de 5 dígitos); CCAA y provincia usan `ine_code` como PK y las FK que las referencian se nombran por su clave (`autonomous_community_ine_code`, `province_ine_code`). `municipality.name` es nullable: los municipios extintos que no estén ni en el gazetteer ni en el 05 de su elección se cargan sin nombre. CERA se modela como pseudo-municipio `<provincia>999` (solo se ingiere su nivel provincial; los totales de CCAA y nación son sumas).
- `silver.polling_station`: mesa, agnóstica a elección; UK (municipio, distrito, sección, código); las pseudo-mesas CERA cuelgan del municipio CERA.
- `silver.election`: tipo + fecha + ámbito (CCAA o municipio; nacional sin ámbito); UK con nulls-not-distinct y CHECK de ámbito único.
- `silver.party`: identidad del partido (nombre, `slug` único, `color`); la carga de
  elecciones resuelve cada **cabecera nacional de candidatura** con la resolución
  compartida de `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo →
  nombre existente → alta con warning). `party.color` se cura en el catálogo
  (clave opcional `color = "#rrggbb"`, validada al cargar) y el resolver la
  materializa en cada recarga, también sobre filas ya existentes; una ficha sin
  `color` deja la fila como esté (`NULL` hoy).
- `silver.party_election`: candidatura por elección (código de fuente, `short_name` y `name` propios); UK (elección, código).
- `silver.turnout`: censo, blancos y nulos por mesa y elección; los votantes se derivan: `sum(vote.votes) + blank_votes + null_votes`.
- `silver.vote`: votos por candidatura y mesa; UK (mesa, candidatura).
- `silver.pollster`: firma encuestadora (nombre, `slug` único).
- `silver.poll`: sondeo del snapshot de Wikipedia; `election_type` obligatorio y `election_id` nullable (la fuente publica sondeos de 2026 sin elección todavía); fechas de campo, muestra, participación y `revision_id` (BIGINT); `source` guarda la cabecera literal; `media` y `reestimator` guardan el medio/comisionante y el autor de la proyección alternativa cuando el literal de la firma los distingue (nulos si no).
- `silver.poll_result`: porcentaje y proyección de escaños (`seats_min`–`seats_max`) de un partido en un sondeo; UK (`poll_id`, `party_id`).

### `gold` — vistas materializadas y vistas de solo lectura para la web

Creadas por migración desde `ingestor/src/ingestor/gold.py` (`matview_ddl()`,
`index_ddl()` y `view_ddl()`); no son tablas y no viven en `silver`: los
agregados y porcentajes solo existen aquí. Las cuatro relaciones de resultados
son **vistas materializadas** con índices y se refrescan con
`uv run ingestor refresh-gold [--concurrently]` (y al final de `ingest` cuando
algún fichero quedó `processed`); las dos de sondeos siguen siendo **vistas**.
La web no agrega hechos; contrato pantalla ↔ vista en
[`../docs/db/gold.md`](../docs/db/gold.md).

- `gold.election_summary` (materializada; `uq_gold_election_summary_election_id`
  único por `election_id`): una fila por elección con censo, nulos, blancos,
  candidaturas, válidos, votantes y `turnout_pct`.
- `gold.result_by_area` (materializada; `uq_gold_result_by_area_grain` único por
  `(election_id, level, community_ine_code, province_ine_code, municipality_id,
  party_id)` con `NULLS NOT DISTINCT` e `ix_gold_result_by_area_province` por
  `(election_id, level, province_ine_code)`): una fila por (elección, nivel,
  área, partido), con `level` en `national` | `community` | `province` |
  `municipality` y `pct` sobre válidos del área.
- `gold.result_by_station` (materializada; `uq_gold_result_by_station_grain`
  único por `(election_id, polling_station_id, party_id)` e
  `ix_gold_result_by_station_municipality` por `(election_id,
  municipality_ine_code)`): una fila por (elección, mesa, partido), con la
  identidad y geografía de la mesa y `pct` sobre válidos de la mesa.
- `gold.station_turnout` (materializada; `uq_gold_station_turnout_grain` único
  por `(election_id, polling_station_id)` e
  `ix_gold_station_turnout_municipality` por `(election_id,
  municipality_ine_code)`): una fila por (elección, mesa) con censo, nulos,
  blancos, candidaturas, válidos, votantes y `turnout_pct`.
- `gold.poll_flat` (vista): una fila por (sondeo, partido) con encuestadora,
  fechas, muestra, participación, `source`/`revision_id`, `pct` y escaños.
- `gold.poll_trend` (vista): la misma fila con `poll_date` =
  `coalesce(fieldwork_end, fieldwork_start)`, ordenada por trabajo de campo
  (`ORDER BY poll_date, poll_id, party_slug`, contractual).

## Fuera del MVP

- Candidatos (fichero 04, con DNI): sin tabla; el MVP no carga personas.
- Agregados 05–08: no se cargan (derivables de 09/10); el 05 solo se usa como fuente de nombres para municipios extintos.
- Senado, autonómicas y municipales: el modelo es extensible, pero van después del MVP.
