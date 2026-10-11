# Modelo de datos

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Fuente de verdad

- ERD de referencia: **`docs/db/schema.drawio`** (draw.io nativo, editable).
- Modelos: **`ingestor/src/ingestor/models.py`** (SQLAlchemy 2).
- Migraciones: **`ingestor/alembic/`** — son la fuente de verdad de la base de datos.
- Esquemas: `bronze` (registro de ingestas), `silver` (hechos normalizados) y `gold` (vistas para el frontend).

## Regla de sincronización (obligatoria)

Todo cambio de modelo se refleja siempre en los tres sitios:

1. ERD — `docs/db/schema.drawio`
2. Modelos — `ingestor/src/ingestor/models.py`
3. Una migración — `ingestor/alembic/versions/`

Nunca se escribe DDL a mano ni ficheros SQL de inicialización. Nunca se edita una migración ya aplicada: se crea otra, a no ser que no se haya aplicado en producción.

## Cambios pendientes de aplicar (acordados)

- **Renombrar el modelo a inglés** ([convención nueva](conventions.md)): election, party, party_election, polling_station, vote, census… El ERD y `models.py` aún usan nombres en español; el mapping completo se cierra al aplicar.
- `eleccion.ano` → `fecha`: en 2019 hubo dos generales y el año no las distingue.
- `voto.candidatura` → `partido_id`, con FK compuesta `(partido_id, eleccion_id)` hacia `partido_eleccion`.
- Nueva tabla `participacion_mesa`: `mesa_id`, `eleccion_id`, `censo`, `votantes`, `votos_nulos`, `votos_blancos`.
- Municipio con `cod_ine` único (5 dígitos); `mesa.cod_muni` y `eleccion.muni_id` lo referencian; `cod_prov` (de mesa y municipio) es FK a provincia.
- `bronze.ingesta` se añade al ERD.
