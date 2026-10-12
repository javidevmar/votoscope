# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-12.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- Sistema de planes de trabajo en [`plans/`](plans/README.md) (reglas).
- Baseline en git: esqueleto commiteado en commits atómicos.
- Proceso: skills de [`skills/`](skills/) instalados pero **fuera de la constitución por ahora**; tests con TDD + pytest; CI diferida al loader.
- **Modelo v2** (inglés) implementado en `models.py`, migración inicial `2a1c9e836128` **aplicada** en local y ERD (`docs/db/schema.drawio`) **regenerado** a v2 (`alembic check` sin drift; `gold` aún vacío).
- **PK natural INE** en `autonomous_community`/`province`: ERD actualizado (`ine_code` como PK; FK a CCAA/provincia renombradas a `autonomous_community_ine_code` / `province_ine_code`); pendiente el sync en `models.py` y migración.

## Pendiente, en orden

1. Cerrar el sync de la PK natural INE (CCAA/provincia) en `models.py` + migración — plan: [`plans/geography-ine-pk.md`](plans/geography-ine-pk.md).
2. Ingesta: spec de los ficheros de entrada, CLI, flujo bronce → plata, política de recarga, validaciones y carga de catálogos geográficos.
3. Entrega: vistas `gold`, contrato gold ↔ front, topología de entornos y scaffold de `web/`.
4. Cierre: menores (README, atribución) y CI (al llegar el loader).

Transversal: logging por niveles (`LOG_LEVEL`) se implementa al montar el primer entrypoint y la web ([conventions.md](conventions.md)).
