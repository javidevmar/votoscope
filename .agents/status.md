# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-12.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- Sistema de planes de trabajo en [`plans/`](plans/README.md) (reglas + primer plan abierto).
- Base de datos levantada; **sin migraciones aplicadas todavía**.

## Pendiente, en orden

0. Baseline en git: commits atómicos del esqueleto actual.
1. Proceso: integrar los skills de [`skills/`](skills/) en la constitución, fijar su convivencia con [`plans/`](plans/README.md) y decidir la política de tests y CI.
2. Modelo v2: cerrar mapping a inglés, tipos/restricciones, identidad (`uuid`), deduplicación de partidos y catálogos geográficos; ERD ↔ modelos ↔ migración — plan: [`plans/model-sync.md`](plans/model-sync.md).
3. Ingesta: spec de los ficheros de entrada, CLI, flujo bronce → plata, política de recarga y validaciones.
4. Entrega: vistas `gold`, contrato gold ↔ front, topología de entornos y scaffold de `web/`.
5. Cierre: menores (README, atribución) y CI completa si se difiere.

Transversal: logging por niveles (`LOG_LEVEL`) se implementa al montar el primer entrypoint y la web ([conventions.md](conventions.md)).
