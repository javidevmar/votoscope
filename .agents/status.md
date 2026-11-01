# Estado y hoja de ruta

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Actualizado: 2026-11-01.

## Hecho

- Repo, `docker-compose.yml` (Postgres 18; host 5434) y esqueleto del ingestador (uv + SQLAlchemy + Alembic).
- Documentación de contexto: este directorio + AGENTS.md por directorio.
- **Arnés SDD**: [`feature_list.json`](../feature_list.json) (cola de trabajo, una feature a la vez), [`specs/`](../specs/) (spec por feature), [`progress/`](../progress/), [`CHECKPOINTS.md`](../CHECKPOINTS.md), [`init.sh`](../init.sh) y subagentes en [`.opencode/agents/`](../.opencode/agents/); proceso en [`specs.md`](specs.md). Sin documentos de iniciativa aparte: el contexto vive en los docs tema y en los specs.
- **Modelo v2** (inglés) implementado en `models.py`; migraciones `2a1c9e836128` (inicial), `06a250c36252` (`municipality.name` nullable), `bcd8a7409aec` (esquema y vistas `gold`) y `9f3c2a1b7d40` (rol de solo lectura de la web) aplicadas en local; ERD ([`../docs/db/schema.drawio`](../docs/db/schema.drawio)) sincronizado (`alembic check` sin drift).
- **Datos de referencia**: generales al Congreso 1986–2023 (nivel MESA) en `refs/congreso/` (gitignored) y gazetteer INE (comunidades, provincias y municipios) en `refs/ine/`; formato, procedencia y rarezas de cada proceso en [`data-sources.md`](data-sources.md).
- **Loader bronce → plata implementado y ejecutado**: parsers por fichero (02/03/05/09/10), adaptador de Congreso, `load-geography`, `ingest <ruta>` (registro por sha256 y recarga por elección), logging por `LOG_LEVEL`, tests con pytest, ruff y CI (`.github/workflows/ingestor.yml`). Las 13 generales cargadas en `silver` en local (65 ficheros en bronce, 106.243 mesas, 6.047.666 votos; sin drift).
- **Sondeos (Wikipedia)**: modelo `pollster`/`poll`/`poll_result` (feature 5), `fetch-polls` (6), lexer de wikitexto (7), adaptador (8) e `ingest-polls` (9) implementados; sincronización 2×/día (10) y ejecución real con cotejo (11) documentadas. Carga real en local (575 sondeos y 6.125 resultados, revisión `1380859635`), y normalización de partidos (12–14) aplicada con `silver` recargado por catálogo.
- **Vistas `gold`** (feature 15): seis vistas de solo lectura creadas por migración (`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat`, `poll_trend`) y contrato pantalla ↔ vista en [`../docs/db/gold.md`](../docs/db/gold.md).
- **Web** (feature 16): scaffold de Next.js 16 (App Router, TypeScript, pnpm, Tailwind 4 y shadcn/ui) en `web/`, con BFF en `app/api/`, logging por `LOG_LEVEL` y rol de solo lectura `votoscope_web`; arranque local con `cd web && pnpm install && pnpm dev`.
- **Cierre** (feature 17): [`../README.md`](../README.md) con qué es el proyecto, puesta en marcha, datos, web, documentación y atribución de fuentes (infoelectoral y Wikipedia CC BY-SA con enlace a la revisión); documentos de contexto al día.
- **Papeles de la firma** (feature 18 `source_norm`): `parse_signature` en el adaptador separa encuestadora, medio (`poll.media`) y reestimador (`poll.reestimator`) del literal de cabecera, sin lista blanca; 575 sondeos recargados en local desde la revisión `1380859635`.
- Proceso: commits atómicos, fixtures herméticos, logging por niveles (`LOG_LEVEL`) en ingestador y web, y rol read-only reflejados en los docs temáticos.

## Pendiente, en orden

La cola de trabajo vive en [`feature_list.json`](../feature_list.json) (una feature a la vez, con estado). En corto:

1. **Rendimiento de `gold`** — feature 19 [`gold_matviews`](../feature_list.json): vistas materializadas e índices para las consultas de resultados.
