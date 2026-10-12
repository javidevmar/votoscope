# PK natural INE en CCAA y provincia

Estado: abierto · Creado: 2026-10-12
Objetivo: cerrar el sync del cambio de PK de `autonomous_community` y `province` a su `ine_code` (ERD hecho; modelos y migración pendientes).

## Notas

- Decisión: los códigos INE de CCAA y provincia son únicos y estables → PK natural; regla actualizada en [conventions.md](../conventions.md).
- FK nombradas por la clave referenciada: `autonomous_community_ine_code` (en `province` y `election`) y `province_ine_code` (en `municipality`); `municipality` conserva `id` + `ine_code` único.
- ERD `docs/db/schema.drawio` al día (validado con la skill `database-erd-drawio`).
- Pendiente: `ingestor/src/ingestor/models.py` + migración (afecta a la UK y el CHECK de `election`). La inicial `2a1c9e836128` solo está aplicada en local, nunca en producción: decidir si se regenera o se crea otra.
- Al cerrar: `alembic check` sin drift y actualizar [data-model.md](../data-model.md) y [status.md](../status.md).
