# Modelo de datos

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Fuente de verdad

- ERD de referencia: **`docs/db/schema.drawio`** (draw.io nativo, editable).
- Modelos: **`ingestor/src/ingestor/models.py`** (SQLAlchemy 2).
- Migraciones: **`ingestor/alembic/`** — son la fuente de verdad de la base de datos.
- Esquemas: `bronze` (registro de ingestas), `silver` (hechos normalizados) y `gold` (vistas para el frontend, aún vacío).

## Regla de sincronización (obligatoria)

Todo cambio de modelo se refleja siempre en los tres sitios:

1. ERD — `docs/db/schema.drawio`
2. Modelos — `ingestor/src/ingestor/models.py`
3. Una migración — `ingestor/alembic/versions/`

Nunca se escribe DDL a mano ni ficheros SQL de inicialización. Nunca se edita una migración ya aplicada: se crea otra, a no ser que no se haya aplicado en producción.

## Modelo v2 (vigente: ERD, modelos y migración)

- En inglés; PK sustitutas `id` (serial) en todas las tablas y códigos naturales únicos aparte.
- `bronze.ingestion`: una fila por fichero fuente (ruta, sha256 único, tamaño, fuente, estado, fecha).
- `silver.autonomous_community` / `province` / `municipality`: geografía con códigos INE (municipio de 5 dígitos). CERA se modela como pseudo-municipio `<provincia>999` (solo se ingiere su nivel provincial; los totales de CCAA y nación son sumas).
- `silver.polling_station`: mesa, agnóstica a elección; UK (municipio, distrito, sección, código); las pseudo-mesas CERA cuelgan del municipio CERA.
- `silver.election`: tipo + fecha + ámbito (CCAA o municipio; nacional sin ámbito); UK con nulls-not-distinct y CHECK de ámbito único.
- `silver.party`: identidad del partido (nombre, `slug` único, color); la carga provisional agrupa por **cabecera nacional de candidatura** (se curará si hace falta).
- `silver.party_election`: candidatura por elección (código de fuente, `short_name` y `name` propios); UK (elección, código).
- `silver.turnout`: censo, blancos y nulos por mesa y elección; los votantes se derivan: `sum(vote.votes) + blank_votes + null_votes`.
- `silver.vote`: votos por candidatura y mesa; UK (mesa, candidatura).
