# Modelo de datos

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Fuente de verdad

- ERD de referencia: **`docs/db/schema.drawio`** (draw.io nativo, editable; una página por esquema y dominio (Bronze, Silver, Bronze polls, Silver polls)).
- Modelos: **`ingestor/src/ingestor/models.py`** (SQLAlchemy 2).
- Migraciones: **`ingestor/alembic/`** — son la fuente de verdad de la base de datos.
- Esquemas: `bronze` (registro de ingestas), `silver` (hechos normalizados) y `gold` (vistas para el frontend, aún vacío).

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
- `silver.party`: identidad del partido (nombre, `slug` único; `color` se curará al construir `gold`). La carga provisional agrupa por **cabecera nacional de candidatura**; la curación acordada la sustituye por un **catálogo versionado** (`src/ingestor/data/party_catalog.toml`: `name` y `aliases` literales ya ingeridos) y un **resolver compartido** (`src/ingestor/parties.py`): normalización → catálogo → nombre existente → alta con warning, sin fuzzy-matching. Criterio: continuidad de la **marca electoral** (las grafías de una misma marca se fusionan; las coaliciones con nombre propio, no). Sin cambio de esquema: la recarga es reingesta (features 12–14).
- `silver.party_election`: candidatura por elección (código de fuente, `short_name` y `name` propios); UK (elección, código).
- `silver.turnout`: censo, blancos y nulos por mesa y elección; los votantes se derivan: `sum(vote.votes) + blank_votes + null_votes`.
- `silver.vote`: votos por candidatura y mesa; UK (mesa, candidatura).
- `silver.pollster`: firma encuestadora (nombre, `slug` único).
- `silver.poll`: sondeo del snapshot de Wikipedia; `election_type` y `election_id` nullable (la fuente publica sondeos de 2026 sin elección todavía); fechas de campo, muestra, participación y `revision_id` (BIGINT); `source` guarda la cabecera literal.
- `silver.poll_result`: porcentaje y proyección de escaños (`seats_min`–`seats_max`) de un partido en un sondeo; UK (`poll_id`, `party_id`).

## Fuera del MVP

- Candidatos (fichero 04, con DNI): sin tabla; el MVP no carga personas.
- Agregados 05–08: no se cargan (derivables de 09/10); el 05 solo se usa como fuente de nombres para municipios extintos.
- Senado, autonómicas y municipales: el modelo es extensible, pero van después del MVP.
