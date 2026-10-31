# Review — feature 17 `close_minor`

**Veredicto:** APPROVED

Rama `feature/close-minor` (apilada sobre `feature/web-scaffold`), cambios en el working tree y sin commits. Revisión independiente con `./init.sh` re-ejecutado, el test nuevo ejecutado aislado, consulta a `silver.poll` para contrastar la revisión de Wikipedia y comprobación manual de enlaces, puerto y frases obsoletas.

## Verificación independiente

- `./init.sh`: **exit 0** — arnés, specs, `uv sync`, `ruff check`, `ruff format`, **242 pytest** verdes y `alembic check` sin drift. La sección web se omite con `[WARN]` porque `web/node_modules` no existe en este checkout; la feature no toca `web/`.
- `cd ingestor && uv run pytest -q tests/test_close_minor.py`: **11 passed** (los 11 tests de documentos, sin skips: R5 corre porque existe `web/package.json`).
- `select distinct revision_id from silver.poll` en el Postgres local: **1380859635**, idéntico al `oldid` del README.
- Enlaces relativos del README comprobados uno a uno (además del test de R9): los 10 targets resuelven (`ingestor/`, `ingestor/.env.example`, `.agents/data-sources.md`, `web/AGENTS.md`, `AGENTS.md`, `.agents/`, `docs/ingestor/ingesta.md`, `docs/db/schema.drawio`, `specs/`, `docs/ingestor/polls-run.md`).
- Comando web contrastado con `web/package.json`: `"dev": "next dev"`, `"build": "next build"`, `"test": "node --env-file-if-exists=.env.local --test"` y `"packageManager": "pnpm@10.28.0"`; el README documenta `pnpm install && pnpm dev`, `pnpm build` y `pnpm test`, sin comandos inventados.
- `oldid` contrastado: README:81 = `.agents/data-sources.md:150` = `docs/ingestor/polls-run.md:5,6,13,14,20,21,33,39,53,67,77,78` = revisión cargada en `silver` (`1380859635`); el snapshot `data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext` existe.
- `5433` ausente en los cuatro ficheros de R12 (`README.md`, `.agents/architecture.md`, `ingestor/.env.example`, `docker-compose.yml`); `5434` presente en README:21 y `ingestor/.env.example:2`, y el comentario de `docker-compose.yml:9` ya dice «5434 because … 5432». `grep -rniE "pendiente|aún no"` en `.agents/architecture.md`, `.agents/environment.md`, `ingestor/AGENTS.md` y `web/AGENTS.md`: sin coincidencias, así que las frases prohibidas de R11 no están.

## Trazabilidad requirements ↔ tests

- R1: [x] `ingestor/tests/test_close_minor.py:31-46` (`test_readme_project_summary`); README:5-11.
- R2: [x] `test_close_minor.py:49-52` (`test_readme_prerequisites`); README:13-17.
- R3: [x] `test_close_minor.py:55-70` (`test_readme_setup`, incluida la comprobación de orden `docker compose` < `uv sync` < `alembic`); README:19-42; `requires-python = ">=3.12"` en `ingestor/pyproject.toml:9`.
- R4: [x] `test_close_minor.py:73-83` (`test_readme_data`); README:44-57.
- R5: [x] `test_close_minor.py:86-97` (`test_readme_web_if_scaffolded`, no se salta: `web/package.json` existe); README:59-63.
- R6: [x] `test_close_minor.py:100-110` (`test_readme_attribution`); README:76-78.
- R7: [x] `test_close_minor.py:100-110` (`test_readme_attribution`: página, `CC BY-SA`, `oldid=`); README:79-83; `oldid` contrastado con la revisión cargada (ver arriba).
- R8: [x] `test_close_minor.py:113-116` (`test_readme_docs_links`); README:65-72.
- R9: [x] `test_close_minor.py:119-121` (`test_readme_relative_links_resolve`), verde; comprobación manual adicional sin fallos.
- R10: [x] `test_close_minor.py:127-133` (`test_status_document_current`); `.agents/status.md:3` (`Actualizado: 2026-10-31`), `:14-16` (15–17 en «Hecho»), `:19-23` (cola en `feature_list.json` con 18 `source_norm`), sin «listos para aprobar» ni «pendiente en la web».
- R11: [x] `test_close_minor.py:136-143` (`test_context_docs_coherent`) + grep manual sin las frases prohibidas en `.agents/architecture.md`, `.agents/environment.md`, `ingestor/AGENTS.md` y `web/AGENTS.md`. `ingestor/AGENTS.md` sin la sección «## Pendiente» (diff borra las 3 líneas finales); `web/AGENTS.md:11-13` describe el scaffold real; `architecture.md:37` dice `5434` y `:17-18` describe `gold` y `web/` en presente.
- R12: [x] `test_close_minor.py:146-155` (`test_port_references`); los cuatro ficheros con `5434` y sin `5433` (ver arriba).

## Tasks completas

- T1: [x] — `test_close_minor.py` creado con helpers y tests del README (R1–R9).
- T2: [x] — `README.md` reescrito (R1–R9), sección web incluida y contrastada con el scaffold.
- T3: [x] — tests de estado y coherencia añadidos (R10–R12).
- T4: [x] — `.agents/status.md` actualizado (R10).
- T5: [x] — coherencia de documentos y ejemplos (R11, R12): `ingestor/AGENTS.md`, `ingestor/.env.example` y `docker-compose.yml` con diff; `.agents/architecture.md`, `.agents/environment.md` y `web/AGENTS.md` ya estaban al día y se verificaron sin cambios.
- T6: [x] — `./init.sh` verde y `progress/impl_close_minor.md` con trazabilidad y evidencia.

Ninguna task queda `[ ]` en `specs/017_close_minor/tasks.md`.

## Checkpoints

- C1: [x] — piezas base y los 4 agentes presentes; `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (17); las `done` pasan los 242 tests; `progress/current.md` describe la sesión activa.
- C3: [x] — sin cambios de modelo (feature de documentos: ERD, `models.py` y migraciones intactos; `alembic check` sin drift); sin DDL a mano ni migraciones editadas; sin dependencias nuevas; sin `print()` ni TODOs.
- C4: [x] en local — 242 pytest, `ruff check`, `ruff format --check` y `alembic check` verdes. Sub-item CI: [ ] no hay run de `ingestor.yml` para la rama porque no se ha pusheado (por diseño del flujo).
- C5: [ ] — pendiente del cierre post-OK: commits atómicos, entrada de la 17 en `progress/history.md` y paso a `done`. El working tree no tiene basura (solo los cambios previstos y los dos ficheros nuevos de la feature); no hay commits ni push, correcto en esta fase.
- C6: [x] — `specs/017_close_minor/` con `requirements.md`, `design.md` y `tasks.md`; requirements en EARS; T1–T6 `[x]`; R1–R12 cubiertos.

## Observaciones no bloqueantes

1. `ingestor/tests/test_close_minor.py:136-143` — `test_context_docs_coherent` no fija expresamente la ausencia de «pendiente en la web» en los cuatro documentos de R11 (solo la comprueba para `.agents/status.md` en `:132-133`). Hoy la frase no está en ninguno (grep manual), así que R11 se cumple; endurecer el test con esa subcadena cerraría el hueco ante ediciones futuras.
2. `test_close_minor.py:146-155` — `test_port_references` comprueba que `5433` no está en `docker-compose.yml`, pero no exige que su comentario diga `5434`; verificado a mano en `docker-compose.yml:9`. Sugerencia de endurecimiento, no defecto actual.
3. La sección web de `init.sh` se omitió por falta de `web/node_modules`; la feature no toca `web/` y `web/package.json` se revisó a mano para R5.

## Cambios requeridos

Ninguno. R1–R12 cubiertos, T1–T6 completas, `./init.sh` verde y la coherencia de puerto, frases obsoletas, enlaces y revisión de Wikipedia verificada contra el repositorio y la base local.
