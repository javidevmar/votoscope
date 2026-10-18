# Review — feature 10 `polls_schedule`

**Veredicto:** APPROVED

Rama `feature/polls-schedule`, working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). Re-review tras los 3 cambios requeridos en la primera pasada. Alcance: `specs/010_polls_schedule/` (T1–T7), `.agents/environment.md`, `.github/workflows/polls-sync.yml`, `ingestor/tests/test_polls_schedule.py`, `progress/impl_polls_schedule.md` y el delta de `specs/010_polls_schedule/design.md` que acompaña a los artefactos. Sin cambios de modelo ni de código de producción.

`./init.sh` re-ejecutado por el reviewer: **verde** — arnés y specs OK, `uv sync`, `ruff check` y `ruff format --check` limpios, **130 tests** (5 de `test_polls_schedule.py`, todos verdes, **sin skips**: Postgres en `:5434`) y `alembic check` sin drift.

## Defectos de la primera review — resueltos

1. **YAML del workflow** — `.github/workflows/polls-sync.yml:22` ya entrecomilla el `name:` (`"Polls sync (placeholder: no deployment environment yet)"`). Verificado con PyYAML y ruamel (YAML 1.2): el fichero parsea y el job `sync` expone los steps esperados (`actions/checkout@v4`, `astral-sh/setup-uv@v7` y el placeholder). El literal de `specs/010_polls_schedule/design.md` (L82) está corregido igual.
2. **Redirect del crontab** — `.agents/environment.md:25` (y `design.md` §«El job») usan `{ …; } >> …/data/polls-sync.log 2>&1`, de modo que el redirect cubre también `fetch-polls`. Comprobado con `/bin/sh -c`: un fallo del primer comando deja su stderr en el log (antes el fichero ni se creaba); el exit code sigue siendo 1. El bullet nuevo de L30 documenta el porqué.
3. **Cobertura de los tests de artefactos** — `test_docs_environment_schedule` (L119–138) añade `Exit code`, `distinto de 0`, `cd /Users/javier/Developer/1poller/ingestor`, `/opt/homebrew/bin/uv`, `docker-compose`, `provisional`, `despliegue` y `} >>`; `test_workflow_skeleton` (L141–157) añade `cron/launchd` y la ausencia de `DATABASE_URL`/`psql`. La tabla de `progress/impl_polls_schedule.md` (L17–19) ya describe lo que los tests comprueban. `design.md` §Tests actualizado en el mismo diff.

## Trazabilidad requirements ↔ tests

- R1: [x] `test_docs_environment_schedule` (L119–138): `fetch-polls`/`ingest-polls` encadenados (`&&` en la entrada de L25), `cd …/ingestor`, `docker-compose` (Postgres local), `Exit code` y `distinto de 0` (semántica de exit en L29).
- R2: [x] mismo test: `0 6,18 * * *`, `crontab`, `launchd`, `data/polls-sync.log`, `cd /Users/javier/Developer/1poller/ingestor`, `/opt/homebrew/bin/uv` y `} >>` (redirect de toda la cadena, L25).
- R3: [x] mismo test: `provisional`, `despliegue` y `polls-sync.yml` (L33).
- R4: [x] `test_workflow_skeleton` (L141–157): `schedule:`, `0 6,18 * * *`, `workflow_dispatch`; además YAML válido verificado en esta review (PyYAML/ruamel).
- R5: [x] mismo test: `placeholder`, `cron/launchd`, ambos comandos y ausencia de `secrets.`, `DATABASE_URL` y `psql`; el job solo hace `echo` (exit 0, sin base de datos).
- R6: [x] `test_no_news_fetch_makes_one_api_call` (L163–177): `main(["fetch-polls"]) == 0`, exactamente una petición, `action=query` y sin `oldid`.
- R7: [x] mismo test: bytes del snapshot intactos (`before`/`after`, L165/L177) y una sola llamada (no hay descarga que lo reescriba).
- R8: [x] `test_no_news_cycle_writes_nothing` (L183–196): primera carga por CLI y ciclo sin novedades con ambos comandos → exit 0.
- R9: [x] mismo test (L190/L199): `_state` compara el nº de filas de `bronze.ingestion` y los ids de `poll`, `poll_result`, `pollster` y `party`; sin filas nuevas ni reemplazo (los ids no cambian). Nota: no compara columnas una a una (p. ej. `pct` in-place); el camino `processed` no hace updates, así que es suficiente.
- R10: [x] mismo test (L188–204): elección sembrada + sondeo pendiente; tras el ciclo el pendiente y `Alpha/Medio` quedan enlazados y `CIS (Target Point)` sigue nulo — el pase de resolución corrió sin snapshots nuevos.
- R11: [x] `test_missing_page_fails_cycle` (L210–219): `main(["fetch-polls"]) == 1` y ERROR en `caplog` con `missing`. El `&&` del cron no se ejercita (es del shell), pero el exit del ciclo es el de `fetch-polls` y queda cubierto.

## Tasks completas

- T1–T7: [x] — 7/7 marcadas en `specs/010_polls_schedule/tasks.md`, sin tasks `[ ]`.

## Checkpoints

- C1: [x] — piezas base del arnés y los 4 agentes presentes; `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#10); features `done` con el suite en verde (130/130); `progress/current.md` describe la sesión activa (re-review incluido).
- C3: [x] — sin cambios de modelo (`models.py`/drawio/Alembic intactos; regla de oro N/A; `alembic check` sin drift); sin DDL a mano; sin dependencias nuevas (`pyproject.toml`/`uv.lock` sin tocar); sin código nuevo de producción (el ciclo son los comandos de 6/9); sin `print()`/TODO en los ficheros de la feature.
- C4: [x] pytest 130/130 (sin skips), ruff check/format limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para la rama (sin commits aún, por diseño del flujo); se disparará con los commits/push post-OK.
- C5: [ ] pendiente del cierre post-veredicto — `git status` sin basura (solo artefactos esperados); `progress/history.md` y commits atómicos pendientes del OK del usuario; `feature_list.json` coherente (#10 sigue `in_progress`, correcto antes del cierre).
- C6: [x] — `specs/010_polls_schedule/` con los 3 archivos; EARS estricto (R1–R11); T1–T7 `[x]`; mapa R↔test en `progress/impl_polls_schedule.md` verificado línea a línea contra el suite, incluidas las cláusulas añadidas (exit code, rutas absolutas, provisional, placeholder sin BD).

## Observaciones no bloqueantes

- `_state` (L100–113) compara ids, no valores columna a columna; aceptable para el camino `processed` actual (el loader no hace updates in-place), pero un cambio futuro del loader a updates in-place no lo detectaría.
- `test_workflow_skeleton` no puede validar YAML sin una dependencia nueva (PyYAML no está aprobado); esta review lo validó a mano con PyYAML y ruamel y el fichero parsea. GitHub volverá a validarlo al hacer push.
- El fallo de `cd` (repo movido) queda fuera del redirect porque el `&&` precede al grupo; no está entre los errores que R1 enumera (página ausente/red/Postgres) y el propio cron reporta el exit code.

## Cambios requeridos

Ninguno.
