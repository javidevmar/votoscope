# Review — feature 11 `polls_run`

**Veredicto:** APPROVED

Rama `feature/polls-run`, working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). La feature 10 ya está cerrada y commiteada (`63027bfc chore(polls_schedule): mark feature 10 done`) y no es objeto de esta revisión. Alcance: `specs/011_polls_run/`, `docs/ingestor/polls-run.md`, `.agents/data-sources.md`, `ingestor/tests/test_polls_run.py` y `progress/impl_polls_run.md`. Sin cambios de modelo (`docs/db/`, `models.py` y Alembic intactos), sin código de producción nuevo y sin dependencias nuevas.

## Cambios requeridos en la review anterior — resueltos

1. **Estado del arnés** — `feature_list.json:151` (#10) está `done` y `:166` (#11) es la única `in_progress`. `./init.sh` re-ejecutado por el reviewer: **exit 0**, con el paso 3 `[OK] feature_list.json válido (18 features)`, `[OK] Specs presentes...` y `[OK] Planes presentes...`.
2. **Enlace de `.agents/data-sources.md`** — `data-sources.md:152` usa `../docs/ingestor/polls-run.md`; la ruta resuelve a `docs/ingestor/polls-run.md` (existe; el resto de enlaces del fichero también resuelven). `test_docs_data_sources` (`test_polls_run.py:240`) exige la subcadena correcta y (`:246`) descarta explícitamente `../../docs/ingestor/polls-run.md`.
3. **T7 con la puerta verde** — `specs/011_polls_run/tasks.md:11` está `[x]` con la evidencia en la línea 12 (`./init.sh` exit 0, pytest 138 passed, ruff limpio, `alembic check` sin drift); `progress/impl_polls_run.md:78–80` y `:82–89` documentan lo mismo y no hay contradicciones.

## Verificación ejecutada por el reviewer

- `./init.sh`: **exit 0** — `uv sync`, `ruff check`, `ruff format`, **138 passed** y `alembic check` sin drift.
- `uv run pytest tests/test_polls_run.py -q -rs`: **8 passed, 0 skipped** (Postgres en `:5434` y snapshot real presentes; los tests de estado no se saltan en local).
- Estado real contra el snapshot y `silver`/`bronze`: snapshot `1380859635.wikitext` (651.942 bytes, sha256 `8a21b27f…b18f50c2`); `bronze.ingestion` lo tiene `processed`, `source=wikipedia-en`, `file_path=polls/wikipedia-en/2026-general/1380859635.wikitext`; `silver.poll` 575 filas con `revision_id=1380859635`, `poll_result` 6.125, `pollster` 28; años de `fieldwork_end` 2023=71, 2024=168, 2025=178, 2026=158; `min(fieldwork_start)=2023-07-24`, `max(fieldwork_end)=2026-10-11`. Coincide con `progress/impl_polls_run.md` y `docs/ingestor/polls-run.md`.
- Completitud recalculada con `poll_tables`/`parse_polls`: 2026 after 2/0/2; 2026 before 160/158/2; 2025 180/178/2; 2024 171/168/3 (2 cabeceras + 1 resultado); 2023 76/71/5 (2 cabeceras + 2 separadoras + 1 resultado); **589 = 575 + 14**. Coincide con `polls-run.md:43–50`.
- Cotejo: las seis filas de `polls-run.md:109–114` se comprobaron contra el wikitexto (líneas 97, 3415, 6967, 10204, 11444 y 5532 del snapshot) y contra `silver`; firma, fechas, PP/PSOE en % y escaños coinciden en las seis. La participación de Ipsos (`66–67`) queda `NULL` en `silver`, como documenta el informe.
- Avisos reales del parseo: `unknown party column: FA`, `unknown party column: FV` y `unparseable turnout: 66–67`; coherentes con `polls-run.md:89–98`.

## Trazabilidad requirements ↔ tests

- R1: [x] `test_snapshot_present_and_registered_processed` (`test_polls_run.py:69`): el `{revid}.wikitext` más reciente de `RAW_DIR` existe y es el registrado. No se contrasta contra la API que sea la «revisión vigente» (suite sin red); la ejecución real y el bronce lo documentan.
- R2: [x] mismo test: fila de `bronze.ingestion` por sha256, `processed`, `source=wikipedia-en` y `file_path` relativo a `RAW_DIR`.
- R3: [x] `test_silver_matches_snapshot_parse` (`:87`): `count(poll where revision_id=revid)` = filas de `parse_polls`; primera y última fila cotejadas (firma, fechas, muestra, turnout).
- R4: [x] mismo test: `count(poll_result)` = resultados del parseo; un resultado cotejado por slug de `party` (pct y escaños).
- R5: [x] `test_silver_covers_year_tables_and_range` (`:127`): `poll_tables` cubre 2023–2026 y hay ≥1 `poll` con `fieldwork_end` en cada año.
- R6: [x] mismo test: `min(fieldwork_start)` entre 2023-07-23 y 2023-08-31 (real: 2023-07-24).
- R7: [x] `test_completeness_arithmetic_no_lost_rows` (`:153`) fija declaradas = cargadas + saltadas y cargadas de `silver` = parseadas; `test_docs_polls_run_completeness` (`:188`) fija el informe; números por tabla y total verificados contra el snapshot (589/575/14).
- R8: [x] `test_docs_polls_run_completeness`: comandos, SQL sobre `silver.poll`, `silver.poll_result` y `bronze.ingestion`, `revision_id` y enlace `oldid=` (`polls-run.md:63–78`).
- R9: [x] `test_docs_polls_run_completeness`: `polls-run.md:80–87` identifica `Lead`, las secciones fuera de *Voting intention estimates* y las columnas sin filas de datos (`FA`, `FV`).
- R10: [x] `test_docs_polls_run_completeness` + verificación manual: informe en `polls-run.md:89–98`; en `silver` la fila de Ipsos tiene `turnout=NULL`.
- R11: [x] `test_docs_polls_run_cotejo` (`:212`): seis filas con `%` y escaños; comprobado a mano que cada fila incluye firma, fechas y dos partidos (PP/PSOE) y que los valores coinciden con el wikitexto y `silver`.
- R12: [x] `test_docs_data_sources` (`:229`): sección, título, formato, contrato del snapshot, comandos y referencia al informe; el enlace `../docs/ingestor/polls-run.md` resuelve y el test descarta la ruta rota.
- R13: [x] `test_docs_data_sources_quirks` (`:249`): `rowspan`, `CIS`, `cabecera`, `2026 (after FA)`, `separador`, `resultado` y `Lead` (`data-sources.md:127–139`).
- R14: [x] mismo test: `cruce de año`, `<2.0`, `fecha de publicación` y `participación` (`data-sources.md:140–147`).
- R15: [x] `test_docs_data_sources`: `CC BY-SA` y `oldid=1380859635` con enlace absoluto correcto (`data-sources.md:148–150`).

## Tasks completas

- T1–T7: [x] — 7/7 marcadas en `specs/011_polls_run/tasks.md`, incluida T7 (`:11`) con la evidencia de la puerta verde (`:12`). Sin tasks `[ ]`.

## Checkpoints

- C1: [x] — piezas base, los 4 agentes presentes y `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#11); #10 `done`; el suite entero en verde (138/138); `progress/current.md` describe la sesión activa (review final de la 11).
- C3: [x] — sin cambios de modelo (`docs/db/`, `models.py`, migraciones intactos); sin DDL a mano; sin dependencias nuevas (`pyproject.toml`/`uv.lock` sin tocar); arquitectura y capas respetadas; sin `print()` ni TODOs en los archivos de la feature.
- C4: [x] — `uv run pytest` 138/138, `ruff check` y `ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] la rama no tiene runs de `ingestor.yml` (los artefactos de la 11 aún no están commiteados; el workflow dispara con `ingestor/**` al hacer push tras el OK del usuario).
- C5: [ ] — pendiente del cierre post-veredicto: no hay entrada nueva en `progress/history.md` ni commits atómicos (llegan con el OK del usuario). No hay archivos temporales ni basura en el working tree, y las features quedan en su estado correcto (#10 `done`, #11 `in_progress`).
- C6: [x] — `specs/011_polls_run/` con los 3 archivos, requirements EARS R1–R15, todas las tasks `[x]` y mapa R↔test en `progress/impl_polls_run.md` verificado línea a línea contra el suite.

## Observaciones no bloqueantes

- `_real_session()` (`test_polls_run.py:42`) crea un engine por test y no lo dispone; con estos 4 tests de estado no tiene impacto, pero conviene `engine.dispose()` si el suite crece.
- Los tests de documentos son de subcadenas; el refuerzo de R12 (`:240`, `:246`) evita que un enlace roto vuelva a pasar desapercibido.
- `test_docs_polls_run_cotejo` no exige explícitamente dos partidos por fila; el contenido se validó a mano en esta review (las seis filas tienen PP y PSOE). El diseño delega el contenido en el reviewer.

## Cambios requeridos

Ninguno.
