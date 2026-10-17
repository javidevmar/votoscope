# Implementación — `polls_fetch` (feature 6)

- **Rama**: `feature/polls-fetch` · **Spec**: `specs/006_polls_fetch/` · **Fecha**: 2026-10-17
- **Estado**: T1–T13 hechas; `./init.sh` verde (ruff check + format, 50 tests, `alembic check` sin drift).
- **Sin commits**: todo queda en el working tree a la espera del `reviewer` y del OK del usuario. No se ha tocado el cambio pendiente de `opencode.json`.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/fetch.py` — resolución de la revisión + descarga del wikitexto (solo stdlib; sin BD) |
| modificar | `ingestor/src/ingestor/cli.py` — subcomando `fetch-polls` con `--page` |
| crear | `ingestor/tests/test_polls_fetch.py` — 22 tests sin red ni base de datos |
| crear | `ingestor/tests/fixtures/wikipedia_polls/api_revision.json` — respuesta real de la API (revid `1380713440`, capturada 2026-10-17) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/api_missing.json` — respuesta real de página ausente |
| modificar | `.agents/architecture.md` (R17) · `ingestor/AGENTS.md` (R18) · `docs/ingestor/ingesta.md` (R19) |

## Trazabilidad R ↔ test

| R | Test(s) |
| --- | --- |
| R1 | `test_parse_revision_response`, `test_resolve_queries_current_revision` |
| R2 | `test_fetch_downloads_fixed_revision` |
| R3 | `test_fetch_downloads_fixed_revision`, `test_fetch_creates_missing_directories` |
| R4 | `test_fetch_skips_existing_revision`, `test_cli_fetch_polls_no_news` |
| R5 | `test_page_option_title_and_dir`, `test_resolve_queries_current_revision` |
| R6 | `test_default_dir`, `test_page_option_title_and_dir` |
| R7 | `test_stdlib_only` |
| R8 | `test_user_agent_header` |
| R9 | `test_timeout_applied` |
| R10 | `test_retry_once_then_success` |
| R11 | `test_retry_gives_up`, `test_download_failure_leaves_no_snapshot` |
| R12 | `test_cli_failure_exit_1` |
| R13 | `test_parse_missing_page_raises` |
| R14 | `test_cli_fetch_polls_downloads`, `test_cli_fetch_polls_no_news` |
| R15 | `test_logs_revision_and_outcome` |
| R16 | `test_no_real_urlopen_used`, `test_resolve_queries_current_revision`, `test_fetch_downloads_fixed_revision`, `test_fetch_skips_existing_revision`, `test_cli_fetch_polls_downloads`, `test_cli_fetch_polls_no_news` |
| R17 | `test_docs_architecture` |
| R18 | `test_docs_ingestor_agents` |
| R19 | `test_docs_ingesta` |

## Desviaciones menores respecto a `design.md` (sin cambio de comportamiento)

1. `test_fetch_queries_current_revision` se implementó como `test_resolve_queries_current_revision` a nivel `resolve_revision`: el orden TDD de `tasks.md` (T3/T4, antes de que exista `fetch_snapshot` en T6) lo exigía; comprueba los mismos parámetros y cubre R1 igual.
2. `test_retry_once_then_success` y `test_retry_gives_up` ejercitan `resolve_revision`; la parte «sin escribir ningún fichero» de R11 se cubre además con `test_download_failure_leaves_no_snapshot` a nivel `fetch_snapshot` (la resolución va bien y falla la descarga).
3. `snapshot_dir`/`snapshot_path` (slug incluido) aterrizaron en T6 junto con la escritura (T6 necesitaba `snapshot_path`); T8 añadió solo el atajo «sin novedades».
4. El fake opener recibe payloads que pueden ser `Exception` (variante explícita de «lanzar `URLError` las N primeras llamadas»): misma capacidad, más legible por test.
5. En los tests de CLI se parchea `ingestor.cli.configure_logging` a no-op para que `basicConfig(force=True)` no desenganche el handler de `caplog` (detalle de test, no de comportamiento).
6. `test_default_dir` añade la normalización `_`→espacio del título (documentada en `design.md` §Ruta del snapshot).

## Verificación

- `cd ingestor && uv run pytest -q` → 50 passed (22 nuevos).
- `./init.sh` (raíz) → verde: arnés + specs, ruff check + format, pytest, `alembic check` sin drift.
- Ningún test usa red ni toca el `data/raw/` real (todo con `tmp_path` y opener inyectado); las fixtures JSON y el recorte de wikitexto son capturas reales del 2026-10-17 (verificadas byte a byte contra la respuesta de la API).
