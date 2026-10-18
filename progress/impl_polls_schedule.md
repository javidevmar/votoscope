# Implementación — `polls_schedule` (feature 10)

Spec: [`specs/010_polls_schedule/`](../specs/010_polls_schedule/). Sin código de
producción ni cambios de modelo: la feature fija el ciclo existente
(`fetch-polls` + `ingest-polls`) con tests y crea los artefactos del job.

## Archivos

- `.agents/environment.md` — sección «Sincronización de sondeos (2×/día)» (R1–R3).
- `.github/workflows/polls-sync.yml` — esqueleto del job programado (R4, R5).
- `ingestor/tests/test_polls_schedule.py` — 5 tests del ciclo y de los artefactos (R1–R11).

## Trazabilidad

| Requirement | Test |
| --- | --- |
| R1 | `test_docs_environment_schedule` (`fetch-polls`/`ingest-polls`, `Exit code`, `distinto de 0`, `docker-compose` y `cd /Users/javier/Developer/1poller/ingestor`) |
| R2 | `test_docs_environment_schedule` (`0 6,18 * * *`, `crontab`, `launchd`, `cd …/ingestor`, `/opt/homebrew/bin/uv`, `data/polls-sync.log` y `} >>`: el redirect cubre la cadena) |
| R3 | `test_docs_environment_schedule` (`provisional`, `despliegue`, `polls-sync.yml`) |
| R4 | `test_workflow_skeleton` (`schedule:`, `0 6,18 * * *`, `workflow_dispatch`) |
| R5 | `test_workflow_skeleton` (`placeholder`, `cron/launchd`, ambos comandos; sin `secrets.`, `DATABASE_URL` ni `psql`) |
| R6 | `test_no_news_fetch_makes_one_api_call` (una petición `action=query`, sin `oldid`, exit 0) |
| R7 | `test_no_news_fetch_makes_one_api_call` (bytes del snapshot intactos) |
| R8 | `test_no_news_cycle_writes_nothing` (`ingest-polls` exit 0 con todo `processed`) |
| R9 | `test_no_news_cycle_writes_nothing` (`_state` intacto: bronce, poll, poll_result, pollster, party) |
| R10 | `test_no_news_cycle_writes_nothing` (sondeo pendiente enlazado sin snapshots nuevos) |
| R11 | `test_missing_page_fails_cycle` (exit 1 + ERROR en el log) |

## Verificación

- `uv run pytest` — 130 passed (Postgres local levantado; los tests de BD corren).
- `uv run ruff check .` y `uv run ruff format --check .` — limpios.
- `./init.sh` — verde.
