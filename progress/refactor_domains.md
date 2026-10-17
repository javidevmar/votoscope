# Refactor estructural: dominios `elections/` y `polls/` (2026-10-17)

Tarea especial del usuario (no SDD): dividir los módulos del ingestador por dominio.
Rama `feature/polls-fetch`. Sin commits (entrega en el working tree). Sin cambios funcionales.

## Movimientos

| Antes | Después | Cómo |
| --- | --- | --- |
| `ingestor/src/ingestor/parsers/` | `ingestor/src/ingestor/elections/parsers/` | `git mv` (conserva historia) |
| `ingestor/src/ingestor/adapters/` | `ingestor/src/ingestor/elections/adapters/` | `git mv` |
| `ingestor/src/ingestor/loaders/` | `ingestor/src/ingestor/elections/loaders/` | `git mv` |
| `ingestor/src/ingestor/fetch.py` (sin trackear) | `ingestor/src/ingestor/polls/fetch.py` | `mv` |
| — | `ingestor/src/ingestor/elections/__init__.py` | nuevo |
| — | `ingestor/src/ingestor/polls/__init__.py` | nuevo |

Imports actualizados: `ingestor.parsers.*` → `ingestor.elections.parsers.*`; `ingestor.adapters.*` → `ingestor.elections.adapters.*`; `ingestor.loaders.*` → `ingestor.elections.loaders.*`; `ingestor.fetch` → `ingestor.polls.fetch` (código, tests y strings de monkeypatch).

Docs con rutas: `ingestor/AGENTS.md`, `docs/ingestor/ingesta.md`, `.agents/plans/polls-wikipedia.md`.

Specs 6–9: rutas de módulos en `design.md` y `tasks.md` → `polls/fetch.py`, `polls/parsers/wikitext.py`, `polls/adapters/wikipedia_polls.py`, `polls/loaders/polls.py` (y `elections/` donde correspondía). Tests planos en `ingestor/tests/`.

## Notas de alcance

- `requirements.md` de los specs 6–9 no se toca (el encargo limita el ajuste a `design.md` y `tasks.md`); quedan menciones de rutas antiguas en esos ficheros (p. ej. spec 7 R16: `parsers/wikitext.py`).
- `progress/impl_polls_fetch.md` y `progress/review_polls_fetch.md` son registros históricos: no se tocan.

## Verificación

- [x] `uv run pytest -q` — **50 passed**
- [x] `uv run ruff check . && uv run ruff format --check .` — limpio (un `I001` en `file09.py` por longitud de línea tras el rename, corregido con `ruff check --fix`)
- [x] `./init.sh` — verde completo, incluido `alembic check` sin drift
- [x] `grep -rn "ingestor\.parsers\|ingestor\.adapters\|ingestor\.loaders\|ingestor\.fetch" ingestor/src ingestor/tests` — sin coincidencias
- [x] `uv run ingestor --help` — los tres subcomandos siguen registrados

## Ficheros tocados

- Movidos: 12 ficheros de `elections/` vía `git mv` (git los registra como renames) + `polls/fetch.py` vía `mv` (sin trackear).
- Nuevos: `elections/__init__.py`, `polls/__init__.py`, `progress/refactor_domains.md`.
- Imports: `cli.py`, `elections/parsers/{__init__,file02,file03,file05,file09,file10}.py`, `elections/adapters/{__init__,congreso}.py`, `elections/loaders/election.py`, `tests/{test_parsers,test_rules,test_polls_fetch}.py`.
- Docs: `ingestor/AGENTS.md`, `docs/ingestor/ingesta.md`, `.agents/plans/polls-wikipedia.md`.
- Specs (design.md/tasks.md): `006_polls_fetch`, `007_polls_lexer`, `008_polls_adapter`, `009_polls_load`.

