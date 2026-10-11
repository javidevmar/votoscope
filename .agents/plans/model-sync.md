# Sync del modelo: renombrado a inglés + cambios acordados
Estado: abierto · Creado: 2026-10-11
Objetivo: dejar el ERD, `models.py` y la migración inicial consistentes entre sí, en inglés y con los cambios acordados; aplicarla en local.

## Mapping de nombres (a cerrar)

| Actual (español) | Propuesto (inglés) |
| --- | --- |
| eleccion | election |
| partido | party |
| partido_eleccion | party_election |
| autonomia | autonomous_community (¿o region?) |
| provincia | province |
| municipio | municipality |
| mesa | polling_station |
| voto | vote |
| participacion_mesa | turnout (¿o polling_station_turnout?) |

Columnas: `cod_*` → `*_code` (cod_ine → ine_code, cod_prov → province_code…), `nombre` → `name`, `ano` → fecha real… Se cierra al aplicar.

## Cambios acordados

- `eleccion.ano` → fecha (en 2019 hubo dos generales y el año no las distingue).
- `voto.candidatura` → `partido_id` con FK compuesta `(partido_id, eleccion_id)` → `partido_eleccion`.
- Nueva tabla `participacion_mesa`: `mesa_id`, `eleccion_id`, `censo`, `votantes`, `votos_nulos`, `votos_blancos`.
- Municipio con `cod_ine` único (5 dígitos); `mesa.cod_muni` y `eleccion.muni_id` lo referencian; `cod_prov` (de mesa y municipio) es FK a provincia.
- `bronze.ingesta` se añade al ERD.

## Pasos

1. Cerrar aquí el mapping de nombres.
2. Actualizar `docs/db/schema.drawio`.
3. Alinear `ingestor/src/ingestor/models.py`.
4. `alembic revision --autogenerate` → revisar (los `CREATE SCHEMA IF NOT EXISTS` se añaden a mano) → `upgrade head` → `alembic check`.
5. Plegar: mapping final a [`../conventions.md`](../conventions.md) y [`../data-model.md`](../data-model.md); borrar este plan.

## Criterio de hecho

`alembic check` sin drift; ERD, modelos y migración con los mismos nombres; migración aplicada en local.
