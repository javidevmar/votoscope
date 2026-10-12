# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-12.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- Sistema de planes de trabajo en [`plans/`](plans/README.md) (reglas).
- Baseline en git: esqueleto commiteado en commits atómicos.
- Proceso: skills de [`skills/`](skills/) instalados pero **fuera de la constitución por ahora**; tests con TDD + pytest; CI diferida al loader.
- **Modelo v2** (inglés, PK sustitutas) implementado en `models.py`, migración inicial `2a1c9e836128` **aplicada** en local y ERD (`docs/db/schema.drawio`) **regenerado** a v2; sync cerrado (`alembic check` sin drift; `gold` aún vacío).

## Pendiente, en orden

1. Ingesta: spec de los ficheros de entrada, CLI, flujo bronce → plata, política de recarga, validaciones y carga de catálogos geográficos.
2. Entrega: vistas `gold`, contrato gold ↔ front, topología de entornos y scaffold de `web/`.
3. Cierre: menores (README, atribución) y CI (al llegar el loader).

Transversal: logging por niveles (`LOG_LEVEL`) se implementa al montar el primer entrypoint y la web ([conventions.md](conventions.md)).
