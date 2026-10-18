# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-10-18.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18; host 5434) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- **Arnés SDD**: [`feature_list.json`](../feature_list.json) (cola de trabajo, una feature a la vez), [`specs/`](../specs/) (spec por feature), [`progress/`](../progress/), [`CHECKPOINTS.md`](../CHECKPOINTS.md), [`init.sh`](../init.sh) y subagentes en [`.opencode/agents/`](../.opencode/agents/); proceso en [`specs.md`](specs.md). Sin documentos de iniciativa aparte: el contexto vive en los docs tema y en los specs.
- **Modelo v2** (inglés) implementado en `models.py`; migraciones `2a1c9e836128` (inicial) y `06a250c36252` (`municipality.name` nullable) aplicadas en local; ERD (`docs/db/schema.drawio`) sincronizado (`alembic check` sin drift; `gold` aún vacío).
- **Datos de referencia**: generales al Congreso 1986–2023 (nivel MESA) en `refs/congreso/` (gitignored) y gazetteer INE (comunidades, provincias y municipios) en `refs/ine/`; formato, procedencia y rarezas de cada proceso en [`data-sources.md`](data-sources.md).
- **Loader bronce → plata implementado y ejecutado**: parsers por fichero (02/03/05/09/10), adaptador de Congreso, `load-geography`, `ingest <ruta>` (registro por sha256 y recarga por elección), logging por `LOG_LEVEL`, tests con pytest, ruff y CI (`.github/workflows/ingestor.yml`). Las 13 generales cargadas en `silver` en local (65 ficheros en bronce, 106.243 mesas, 6.047.666 votos; sin drift).
- **Sondeos (Wikipedia)**: modelo `pollster`/`poll`/`poll_result` (feature 5), `fetch-polls` (6), lexer de wikitexto (7), adaptador (8) e `ingest-polls` (9) implementados; carga real en local (575 sondeos y 6.125 resultados, revisión `1380777984`). Specs de la sincronización 2×/día (10), la ejecución real (11) y la normalización de partidos (12–14) listos para aprobar.
- Proceso: commits atómicos, fixtures herméticos y rol read-only de la web (al scaffold) reflejados en los docs temáticos.

## Pendiente, en orden

La cola de trabajo vive en [`feature_list.json`](../feature_list.json) (una feature a la vez, con estado). En corto:

1. **Sondeos (Wikipedia)** — features 10–11 (specs en [`specs/010_polls_schedule/`](../specs/010_polls_schedule/) y [`specs/011_polls_run/`](../specs/011_polls_run/)): job de sincronización 2×/día y ejecución real con conteo de completitud y cotejo.
2. **Party-norm** — features 12–14 (specs en [`specs/`](../specs/)): catálogo de partidos, recarga de `silver` y sondeos por catálogo.
3. **Entrega y cierre** — features 15–17: vistas `gold` + contrato gold ↔ front + topología de entornos, scaffold de `web/` y README/atribución; 18 `source_norm`: normalización de las fuentes de los sondeos.

Transversal: logging por niveles (`LOG_LEVEL`) hecho en el ingestador; pendiente en la web ([conventions.md](conventions.md)).
