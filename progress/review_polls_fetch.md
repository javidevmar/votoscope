# Review — feature 6 `polls_fetch`

**Veredicto:** APPROVED

Rama `feature/polls-fetch`, working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). `./init.sh` re-ejecutado por el reviewer: verde — arnés + specs, `ruff check`/`ruff format --check` limpios, 50 tests (22 nuevos) y `alembic check` sin drift contra el Postgres de `:5434`.

Diff revisado: `ingestor/src/ingestor/polls/fetch.py` (nuevo), `ingestor/src/ingestor/cli.py`, `ingestor/tests/test_polls_fetch.py` + `ingestor/tests/fixtures/wikipedia_polls/` (nuevos), `.agents/architecture.md`, `ingestor/AGENTS.md`, `docs/ingestor/ingesta.md`.

Verificación en vivo adicional del reviewer (red disponible, ningún test la usa): `api_revision.json` y `api_missing.json` son byte a byte idénticas a las respuestas actuales de la API, y el recorte `WIKITEXT` del test es prefijo exacto del `oldid=1380713440` (`index.php?oldid=…&action=raw`).

## Trazabilidad requirements ↔ tests

Tests: `ingestor/tests/test_polls_fetch.py` (22, todos en verde, sin red ni BD — opener inyectado y `tmp_path`).

- R1: [x] `test_resolve_queries_current_revision` (L92–103: igualdad estricta de los 7 parámetros) + `test_parse_revision_response` (L79–80).
- R2: [x] `test_fetch_downloads_fixed_revision` (L133–143: `RAW_URL` + `oldid={revid}&action=raw`).
- R3: [x] `test_fetch_downloads_fixed_revision` (ruta exacta y bytes escritos) + `test_fetch_creates_missing_directories` (L146–149).
- R4: [x] `test_fetch_skips_existing_revision` (L159–167: 1 sola llamada, contenido intacto, `downloaded=False`) + `test_cli_fetch_polls_no_news` (L202–212).
- R5: [x] `test_page_option_title_and_dir` (L170–178: otra página cambia `titles` y aterriza en su slug). Matiz no bloqueante sobre el tramo CLI del `--page`: ver observaciones.
- R6: [x] `test_default_dir` (L181–187: `2026-general`, normalización `_`→espacio y slug de 2027) + `test_page_option_title_and_dir`.
- R7: [x] `test_stdlib_only` (L247–252: sin `requests`/`httpx` en `sys.modules`; `urlopen` de `urllib.request`); `pyproject.toml`/`uv.lock` sin cambios en el diff.
- R8: [x] `test_user_agent_header` (L106–109).
- R9: [x] `test_timeout_applied` (L112–115: `timeout == 30`).
- R10: [x] `test_retry_once_then_success` (L118–123: 2 llamadas + WARNING «retrying once»).
- R11: [x] `test_retry_gives_up` (L126–130) + `test_download_failure_leaves_no_snapshot` (L152–156: ningún `*.wikitext`).
- R12: [x] `test_cli_failure_exit_1` (L215–222: `main(...) == 1` + ERROR en log).
- R13: [x] `test_parse_missing_page_raises` (L83–85); el orden lineal de `fetch_snapshot` (`fetch.py` L121–126) garantiza que no se intenta la descarga.
- R14: [x] `test_cli_fetch_polls_downloads` (L190–199) + `test_cli_fetch_polls_no_news` (ambos exit 0).
- R15: [x] `test_logs_revision_and_outcome` (L225–234: `revid=`, «downloaded snapshot» y «up to date» a INFO). Matiz sobre `timestamp=`: ver observaciones.
- R16: [x] `test_no_real_urlopen_used` (L237–244) + el resto de tests con opener inyectado; fixtures JSON reales (verificadas en vivo, arriba).
- R17: [x] `test_docs_architecture` (L255–259); diff de `.agents/architecture.md` con la excepción CLI y la ruta del bronce de sondeos.
- R18: [x] `test_docs_ingestor_agents` (L262–266); diff de `ingestor/AGENTS.md` (comando, `fetch.py` y matiz).
- R19: [x] `test_docs_ingesta` (L269–272); sección nueva en `docs/ingestor/ingesta.md` (comportamiento, ruta, timeout/reintento, exit codes).

## Tasks completas

- T1–T13: [x] — todas marcadas en `specs/006_polls_fetch/tasks.md`; sin tasks `[ ]`.
- Desviaciones 1–6 de `progress/impl_polls_fetch.md` valoradas: todas son de nivel de test o de reparto T6/T8 sin cambio de comportamiento (la 1 y la 6 están amparadas por el propio `design.md`; la 4 es del fake). No alteran ninguna verificación.

## Checkpoints

- C1: [x] — piezas base del arnés y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#6; validado por `init.sh` §3); features 1–5 `done` con el suite en verde (50/50); `progress/current.md` describe la sesión activa.
- C3: [x] — sin cambios de modelo (ni `models.py`, ni drawio, ni Alembic; `alembic check` sin drift); sin DDL; sin dependencias nuevas (`pyproject.toml`/`uv.lock` intactos); logging por módulo y formateo perezoso (`fetch.py` L99, L108, L124, L129), nivel por `LOG_LEVEL`; sin `print()`/TODO; arquitectura respetada (`fetch.py` sin BD; excepción «descarga por CLI» documentada).
- C4: [x] en local — pytest 50/50 (22 nuevos), `ruff check` y `ruff format --check` limpios, `alembic check` sin drift; fixtures verificadas en vivo contra la API. Sub-item CI: [ ] sin run de `ingestor.yml` (rama sin commits/push aún, por diseño del flujo); el workflow ejecuta exactamente estos gates — dispararlo con el push/PR.
- C5: [ ] pendiente del cierre post-veredicto — sin archivos temporales de la feature (`git status` solo lista los artefactos esperados); `progress/history.md` con la última sesión cerrada; `feature_list.json` coherente; commits atómicos pendientes del OK del usuario (por diseño).
- C6: [x] — `specs/006_polls_fetch/` con los 3 archivos; EARS con ids estables y tabla acceptance↔R; T1–T13 `[x]`; mapa de trazabilidad R1–R19 en `progress/impl_polls_fetch.md`.

## Observaciones no bloqueantes (no exigen cambios)

1. R5 — el test verifica la conducta a nivel de función, pero no el tramo argparse (`cli.py` L48–52 → L60: `fetch_snapshot(args.page, …)`). Un caso `main(["fetch-polls", "--page", "Opinion polling for the 2027 …"])` que compruebe `titles` y el slug cerraría el círculo cuando se vuelva a tocar el CLI (features 10/11).
2. R15 — el test no fija la subcadena `timestamp=` de la línea de log (`fetch.py` L108); añadirla si se quiere congelar el contrato completo.
3. Alcance — `.opencode/agents/spec-author.md`, `feature_list.json` (7–9 `spec_ready`), `specs/polls_{lexer,adapter,load}/` y `opencode.json` están en el working tree pero pertenecen a las features 7–9 o al usuario: fuera de esta revisión.

## Cambios requeridos

Ninguno.
