# Tareas — `polls_model`

TDD donde aplica (tests primero en T1 y T5). Cada task es un commit atómico.

- [x] T1 — Crear `ingestor/tests/test_polls_model.py` con los tests de metadata de las tres tablas (columnas, tipos, nullability, PK, FK, índices de `poll_result`, UK y CHECK). En rojo: los modelos no existen. Cubre: R1–R10.
- [x] T2 — Añadir `Pollster`, `Poll` y `PollResult` a `ingestor/src/ingestor/models.py` según `design.md`. `uv run pytest tests/test_polls_model.py` en verde. Cubre: R1–R10.
- [x] T3 — `uv run alembic revision --autogenerate -m "polls model"`; revisar la migración (solo las tres tablas; el esquema `silver` ya existe) y aplicar `uv run alembic upgrade head` contra el Postgres de `:5434`. Cubre: R11.
- [x] T4 — `uv run alembic check`: sin drift. Cubre: R12.
- [x] T5 — Añadir a `ingestor/tests/test_polls_model.py` los tests de sincronización de documentación (parseo con `xml.etree.ElementTree` de `docs/db/schema.drawio`: páginas «Silver polls» y «Bronze polls»; y de `.agents/data-model.md`: regla y tablas nuevas). En rojo. Cubre: R13–R15.
- [x] T6 — ERD en `docs/db/schema.drawio` según `design.md`, validado con la skill `database-erd-drawio`. Cubre: R13, R14.
- [x] T7 — Actualizar `.agents/data-model.md`: «una página por esquema y dominio (Bronze, Silver, Bronze polls, Silver polls)» + bullets de `pollster`, `poll` y `poll_result` en el modelo v2. Cubre: R15.
- [x] T8 — Puerta final: `./init.sh` en verde (ruff, pytest, `alembic check`). Cubre: R1–R15.
