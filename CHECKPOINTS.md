# CHECKPOINTS — Evaluación del estado final

## C1 — El arnés está completo

- [ ] Existen las piezas base: `AGENTS.md`, `init.sh`, `feature_list.json`,
      `progress/current.md`, `CHECKPOINTS.md`, `.agents/specs.md`.
- [ ] Existen los 4 agentes en `.opencode/agents/`: `leader`, `spec-author`,
      `implementer`, `reviewer`.
- [ ] `./init.sh` termina con exit code 0.

## C2 — El estado es coherente

- [ ] Como mucho una feature en `in_progress` en `feature_list.json`.
- [ ] Toda feature `done` tiene sus tests en verde.
- [ ] `progress/current.md` está vacío o describe la sesión activa
      (no contiene basura de sesiones anteriores).

## C3 — El código respeta las reglas del repo

- [ ] Modelo sincronizado en los tres sitios: `docs/db/schema.drawio` ↔
      `ingestor/src/ingestor/models.py` ↔ migraciones Alembic (`alembic check`
      sin drift cuando la base está levantada).
- [ ] Nada de DDL a mano ni SQL de inicialización; ninguna migración ya
      aplicada editada.
- [ ] Capas y arquitectura según [`.agents/architecture.md`](.agents/architecture.md).
- [ ] Sin dependencias nuevas sin consentimiento explícito del usuario
      ([`.agents/conventions.md`](.agents/conventions.md)).
- [ ] Logging por niveles con `LOG_LEVEL` (nunca hardcodeado, nunca secretos).
- [ ] No hay `print()` sueltos para debug, ni TODOs sin contexto.

## C4 — La verificación es real

- [ ] `uv run pytest` en `ingestor/` con todos los tests verdes.
- [ ] `uv run ruff check .` y `uv run ruff format --check .` limpios.
- [ ] `uv run alembic check` sin drift en local (con el Postgres levantado).
- [ ] La CI (`ingestor.yml`) está verde para la rama de trabajo.

## C5 — La sesión se cerró bien

- [ ] No hay archivos temporales ni basura sin trackear (`__pycache__` fuera
      del `.gitignore`, `*.tmp`, `.DS_Store`…).
- [ ] `progress/history.md` tiene una entrada por la última sesión.
- [ ] Cada feature trabajada quedó en su estado correcto en `feature_list.json`.
- [ ] Los commits son atómicos y la documentación afectada se actualizó en el
      mismo commit que el cambio.

## C6 — Spec Driven Development

- [ ] Toda feature con `"sdd": true` en estado `spec_ready`, `in_progress` o
      `done` tiene su carpeta `specs/<name>/` con los 3 archivos:
      `requirements.md`, `design.md`, `tasks.md`.
- [ ] `requirements.md` usa EARS estricto (ver [`.agents/specs.md`](.agents/specs.md)).
- [ ] Toda feature `done` con `"sdd": true` tiene todas sus tasks marcadas `[x]`.
- [ ] Cada `R<n>` de `requirements.md` está cubierto por al menos un test
      concreto en `ingestor/tests/` (mapa en `progress/impl_<name>.md`).
