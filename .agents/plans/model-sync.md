# Sync del modelo v2: falta el ERD
Estado: hecho · Creado: 2026-10-11 · Abierto: 2026-10-11 · Hecho: 2026-10-12 · Actualizado: 2026-10-12
Objetivo: dejar `docs/db/schema.drawio` alineado con el modelo v2 ya implementado y aplicado.

## Hecho

- Modelos v2 (inglés, PK sustitutas `id`, códigos naturales únicos) y migración inicial `2a1c9e836128` aplicada en local; `alembic check` sin drift.
- Identidad de partidos/candidaturas resuelta: `party.slug` único y `party_election` con `code`, `short_name` y `name` por elección.
- `turnout` (censo, blancos, nulos; votantes derivados) y CERA como pseudo-municipio/mesa.

## Falta

1. Regenerar `docs/db/schema.drawio` con el diseño v2 (draw.io nativo; validar con el validador del skill de ERD). El actual queda obsoleto por completo: se regenera, no se parchea.
2. Tras el ERD: `uv run alembic check` sin drift y plegar este plan (lo durable ya vive en [`../data-model.md`](../data-model.md) y [`../conventions.md`](../conventions.md)).
