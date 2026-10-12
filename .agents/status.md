# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-12.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- Sistema de planes de trabajo en [`plans/`](plans/README.md) (reglas).
- Baseline en git: esqueleto commiteado en commits atómicos.
- Proceso: skills de [`skills/`](skills/) instalados pero **fuera de la constitución por ahora**; tests con TDD + pytest; CI diferida al loader.
- **Modelo v2** (inglés) implementado en `models.py`, migración inicial `2a1c9e836128` **aplicada** en local y ERD (`docs/db/schema.drawio`) **regenerado** a v2 (`alembic check` sin drift; `gold` aún vacío).
- **PK natural INE** en `autonomous_community`/`province` cerrada: ERD, `models.py` y migración sincronizados (la inicial `2a1c9e836128` se regeneró en el sitio por no estar aplicada nunca en producción; FK renombradas a `autonomous_community_ine_code` / `province_ine_code`; `alembic check` sin drift).
- **Datos de referencia**: generales al Congreso 1986–2023 (nivel MESA) descargadas y descomprimidas en `refs/congreso/` (local, gitignored); formato y variaciones en [`data-sources.md`](data-sources.md).
- **Especificación cerrada** (ronda de decisiones 2026-10-12): spec de ingesta en [`plans/ingest-spec.md`](plans/ingest-spec.md); commits atómicos, ruff, CI al loader, fixtures herméticos y rol read-only de la web (al scaffold) reflejados en los docs temáticos.

## Pendiente, en orden

1. Ingesta: implementar el loader según [`plans/ingest-spec.md`](plans/ingest-spec.md).
2. Entrega: vistas `gold`, contrato gold ↔ front, topología de entornos y scaffold de `web/`.
3. Cierre: menores (README, atribución) y CI (al llegar el loader).

Transversal: logging por niveles (`LOG_LEVEL`) se implementa al montar el primer entrypoint y la web ([conventions.md](conventions.md)).
