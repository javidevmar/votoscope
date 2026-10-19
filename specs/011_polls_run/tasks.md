# Tareas — `polls_run`

Ejecución y documentación: sin código de producción, sin modelo y sin dependencias (ERD ↔ `models.py` ↔ migración no aplican). El estado real de la carga es **evidencia operativa** (comandos y SQL reproducible en el informe y en `progress/impl_polls_run.md`), sin tests de estado. TDD: los tests de documentos nacen rojos. Detalle en [`design.md`](design.md).

- [x] T1 — Dejar constancia de la evidencia operativa de R1–R7 (snapshot en disco y registro `processed`; `silver` = parseo; anualidades y rango del trabajo de campo; aritmética de completitud) en `docs/ingestor/polls-run.md` y `progress/impl_polls_run.md`, con comandos y SQL reproducible. Cubre: R1–R7.
- [x] T2 — Ejecutar el ciclo real desde `ingestor/` sobre el Postgres local: `uv run ingestor fetch-polls` y `uv run ingestor ingest-polls`; registrar comandos, salida, exit codes y avisos del adaptador. Evidencia de R1–R6 anotada en el informe y el impl. Fetch o ingesta fallidos → parar y documentar (`blocked`). Cubre: R1–R6.
- [x] T3 — Tests de documentación del informe (`test_docs_polls_run_completeness`, `test_docs_polls_run_cotejo`) en rojo. Cubre: R7–R11.
- [x] T4 — Escribir `docs/ingestor/polls-run.md` (estructura y subcadenas en `design.md`: comandos, completitud por tabla con la referencia ≈584, aritmética, método SQL, fuera de alcance, avisos, cotejo de ≥5 sondeos con enlace `oldid`). Tests verdes. Cubre: R7–R11.
- [x] T5 — Tests de documentación de la fuente (`test_docs_data_sources`, `test_docs_data_sources_quirks`) en rojo. Cubre: R12–R15.
- [x] T6 — Escribir la sección «Sondeos (Wikipedia)» en `.agents/data-sources.md` (formato, rarezas, licencia CC BY-SA con `oldid`, referencia al informe). Tests verdes. Cubre: R12–R15.
- [x] T7 — Puerta final: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` y `./init.sh` en verde; escribir `progress/impl_polls_run.md` con la evidencia de la ejecución y la trazabilidad R1–R15 (R1–R7 evidencia operativa; R7–R15 tests de documentos). Cubre: R1–R15.
  - Puerta verde: `./init.sh` exit 0 tras cerrar la #10 (una sola feature `in_progress`, la 11; cambio nº 1 del review). `uv run pytest` 136 passed, ruff check/format limpios y `alembic check` sin drift.
- Nota (2026-10-19): por decisión aprobada del usuario se retiran los tests de estado que leían `data/raw/` y el `silver` local; R1–R7 se verifican con la evidencia operativa del informe y `progress/impl_polls_run.md`. La infraestructura de tests usa una base de datos temporal por sesión, independiente de la BD de la aplicación.
