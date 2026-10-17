# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-17.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18; host 5434) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- Sistema de planes de iniciativa en [`plans/`](plans/README.md) (reglas) y, sobre él, el **arnés SDD**: [`feature_list.json`](../feature_list.json) (cola de trabajo, una feature a la vez), [`specs/`](../specs/) (spec por feature), [`progress/`](../progress/), [`CHECKPOINTS.md`](../CHECKPOINTS.md), [`init.sh`](../init.sh) y subagentes en [`.opencode/agents/`](../.opencode/agents/); proceso en [`specs.md`](specs.md).
- **Modelo v2** (inglés) implementado en `models.py`; migraciones `2a1c9e836128` (inicial) y `06a250c36252` (`municipality.name` nullable) aplicadas en local; ERD (`docs/db/schema.drawio`) sincronizado (`alembic check` sin drift; `gold` aún vacío).
- **Datos de referencia**: generales al Congreso 1986–2023 (nivel MESA) en `refs/congreso/` (gitignored) y gazetteer INE (comunidades, provincias y municipios) en `refs/ine/`; formato, procedencia y rarezas de cada proceso en [`data-sources.md`](data-sources.md).
- **Loader bronce → plata implementado y ejecutado**: parsers por fichero (02/03/05/09/10), adaptador de Congreso, `load-geography`, `ingest <ruta>` (registro por sha256 y recarga por elección), logging por `LOG_LEVEL`, tests con pytest, ruff y CI (`.github/workflows/ingestor.yml`). Las 13 generales cargadas en `silver` en local (65 ficheros en bronce, 106.243 mesas, 6.047.666 votos; sin drift).
- Proceso: commits atómicos, fixtures herméticos y rol read-only de la web (al scaffold) reflejados en los docs temáticos.

## Pendiente, en orden

La cola de trabajo vive en [`feature_list.json`](../feature_list.json) (una feature a la vez, con estado). En corto:

1. **Sondeos desde Wikipedia (generales 2026)** — features 5–11: modelo (`pollster`, `poll`, `poll_result`), `fetch-polls`, lexer de wikitexto, adaptador, `ingest-polls`, job de sincronización 2×/día y ejecución real; contexto de diseño en [`plans/polls-wikipedia.md`](plans/polls-wikipedia.md).
2. **Entrega** — features 12–13: vistas `gold` + contrato gold ↔ front + topología de entornos, y scaffold de `web/`.
3. **Cierre** — feature 17: README y atribución.

Transversal: logging por niveles (`LOG_LEVEL`) hecho en el ingestador; pendiente en la web ([conventions.md](conventions.md)).
