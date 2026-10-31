# Implementación — `close_minor` (feature 17)

- **Rama:** `feature/close-minor` (apilada sobre `feature/web-scaffold`), cambios en el working tree, sin commits.
- **Estado:** implementación completa; T1–T6 `[x]` en [`../specs/017_close_minor/tasks.md`](../specs/017_close_minor/tasks.md). Pendiente: revisión del `reviewer` y OK del usuario.
- **Alcance:** solo documentos y tests de documentos. Sin código de aplicación, sin cambios de modelo ni de dependencias.

## Qué se ha hecho

- **T1/T3 — tests** (`ingestor/tests/test_close_minor.py`): helpers `REPO_ROOT`, `_read`, `_relative_links` y 11 tests de solo lectura (sin red ni base) que fijan R1–R12. Primero en rojo (7 tests del README y, tras T2, los 2 de estado/puerto), luego en verde.
- **T2 — README** (`README.md`): reescrito en español con qué es Votoscope, requisitos, puesta en marcha (Docker/Postgres 18 en `localhost:5434`, `uv sync`, `alembic upgrade head`, `pytest`), datos (`data/raw/congreso`, `refs/ine` y comandos del CLI), web, documentación enlazada y fuentes/atribución.
- **T4 — estado** (`.agents/status.md`): fecha `Actualizado: 2026-10-31`; features 15 (vistas `gold`), 16 (web) y 17 (README/atribución) en «Hecho»; cola pendiente apuntando a `feature_list.json` con la 18 `source_norm`; revisión de sondeos corregida a `1380859635`; retiradas las frases «listos para aprobar» y «pendiente en la web».
- **T5 — coherencia**: `ingestor/AGENTS.md` sin la sección «Pendiente»; `ingestor/.env.example` y el comentario de `docker-compose.yml` con `5434`. `.agents/architecture.md`, `.agents/environment.md` y `web/AGENTS.md` ya estaban al día por las features 15/16 (se verificaron; sin diff).

## Sección web del README (R5)

**Incluida.** `web/package.json` existe (feature 16 entregada), con `"packageManager": "pnpm@10.28.0"` y script `"dev": "next dev"`; el README documenta el comando real `cd web && pnpm install && pnpm dev` (más `pnpm build` y `pnpm test`) y que los datos se leen de las vistas `gold` en servidor vía el BFF de `web/app/api/`. No se inventaron comandos.

## Atribución de Wikipedia (R7)

Enlace citado: `https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid=1380859635`.

Contrastado con la revisión realmente cargada/documentada:

- `.agents/data-sources.md` §«Sondeos (Wikipedia)» cita `oldid=1380859635`.
- `docs/ingestor/polls-run.md` documenta la ejecución real con `revision_id`/`oldid` `1380859635` y su snapshot `data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext` (presente en disco).

## Trazabilidad R ↔ test

| R | Test(s) en `ingestor/tests/test_close_minor.py` |
| --- | --- |
| R1 | `test_readme_project_summary` |
| R2 | `test_readme_prerequisites` |
| R3 | `test_readme_setup` |
| R4 | `test_readme_data` |
| R5 | `test_readme_web_if_scaffolded` (no se salta: existe `web/package.json`) |
| R6 | `test_readme_attribution` |
| R7 | `test_readme_attribution` |
| R8 | `test_readme_docs_links` |
| R9 | `test_readme_relative_links_resolve` |
| R10 | `test_status_document_current` |
| R11 | `test_context_docs_coherent` |
| R12 | `test_port_references` |

## Evidencias de verificación (2026-10-31, local)

- `cd ingestor && uv run pytest` → **242 passed**.
- `cd ingestor && uv run ruff check .` → **All checks passed!**
- `cd ingestor && uv run ruff format --check .` → **49 files already formatted**.
- `./init.sh` → **verde** (arnés, specs, ruff, pytest y `alembic check` sin drift). Aviso no bloqueante: `web/node_modules` no existe en este checkout, así que `init.sh` omite `pnpm test`/`pnpm lint` de la web (la feature no toca `web/`).

## Desviaciones respecto al spec

Ninguna. Las tareas se ejecutaron en orden T1–T6. `.agents/architecture.md`, `.agents/environment.md` y `web/AGENTS.md` no necesitaron cambios porque las features 15/16 ya los habían actualizado; el spec/design lo preveía («verifica y corrige solo lo que siga obsoleto»).
