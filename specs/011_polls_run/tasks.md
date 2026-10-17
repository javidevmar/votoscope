# Tareas — `polls_run`

Ejecución y documentación: sin código de producción, sin modelo y sin dependencias (ERD ↔ `models.py` ↔ migración no aplican). Los tests de estado son de solo lectura y se saltan sin Postgres o sin snapshot. TDD: los tests de documentos nacen rojos; los de estado pueden nacer verdes si una ejecución previa ya cargó el snapshot (hoy lo está) — la task T2 re-ejecuta el ciclo para dejar la evidencia. Detalle en [`design.md`](design.md).

- [ ] T1 — Crear `ingestor/tests/test_polls_run.py` con los helpers (`_newest_snapshot`, `_real_session`) y los tests de estado: snapshot en disco + registro `processed` en bronce (R1, R2); `silver` = parseo del snapshot (R3, R4); anualidades 2023–2026 y rango desde el 23-jul-2023 (R5, R6); aritmética de completitud sin filas perdidas (R7, parte de estado). Si el snapshot más reciente no está cargado, en rojo. Cubre: R1–R7.
- [ ] T2 — Ejecutar el ciclo real desde `ingestor/` sobre el Postgres local: `uv run ingestor fetch-polls` y `uv run ingestor ingest-polls`; registrar comandos, salida, exit codes y avisos del adaptador. Tests de T1 verdes. Fetch o ingesta fallidos → parar y documentar (`blocked`). Cubre: R1–R6.
- [ ] T3 — Tests de documentación del informe (`test_docs_polls_run_completeness`, `test_docs_polls_run_cotejo`) en rojo. Cubre: R7–R11.
- [ ] T4 — Escribir `docs/ingestor/polls-run.md` (estructura y subcadenas en `design.md`: comandos, completitud por tabla con la referencia ≈584, aritmética, método SQL, fuera de alcance, avisos, cotejo de ≥5 sondeos con enlace `oldid`). Tests verdes. Cubre: R7–R11.
- [ ] T5 — Tests de documentación de la fuente (`test_docs_data_sources`, `test_docs_data_sources_quirks`) en rojo. Cubre: R12–R15.
- [ ] T6 — Escribir la sección «Sondeos (Wikipedia)» en `.agents/data-sources.md` (formato, rarezas, licencia CC BY-SA con `oldid`, referencia al informe). Tests verdes. Cubre: R12–R15.
- [ ] T7 — Puerta final: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` y `./init.sh` en verde; escribir `progress/impl_polls_run.md` con la evidencia de la ejecución y la trazabilidad R1–R15 ↔ tests. Cubre: R1–R15.
