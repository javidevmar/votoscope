# Arquitectura

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Qué es

Votoscope es un agregador de resultados electorales de España.

- **MVP**: las últimas elecciones generales (Congreso), con resultados por **mesa** (la unidad más fina publicada), a partir de ficheros fuente descargados en local.
- **Diseño extensible**: después, Senado, procesos anteriores y elecciones autonómicas/municipales, sin rehacer el esquema; en el ingestador, un adaptador por proceso electoral (todas las del Congreso comparten el suyo), desacoplados — ver [`../ingestor/AGENTS.md`](../ingestor/AGENTS.md).

## Dos partes

1. **Ingestador — `ingestor/` (Python)**: pipeline bronce → plata → oro sobre PostgreSQL.
   - **Bronce**: ficheros originales, inmutables, en `data/raw/`, más un registro por fichero en `bronze.ingestion` (ruta, sha256, tamaño, fuente, estado). Un fichero corregido entra como fichero nuevo.
   - **Plata**: tablas normalizadas en el esquema `silver`. Sin agregados.
   - **Oro**: seis vistas de solo lectura en el esquema `gold`, creadas por migración desde `ingestor/src/ingestor/gold.py` (`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat`, `poll_trend`). Los agregados y porcentajes solo existen aquí; la web no los recalcula. Contrato pantalla ↔ vista: [`../docs/db/gold.md`](../docs/db/gold.md).
2. **Frontend — `web/` (Next.js 16, App Router, TypeScript)**: scaffold hecho con pnpm 10.28, Tailwind CSS 4 y shadcn/ui. Lee las vistas `gold` a través de un BFF obligatorio en `web/app/api/` (Route Handlers y módulos privados `_lib/`): toda llamada a PostgreSQL o a servicios externos vive ahí y el navegador no accede a la base. Render en servidor (Server Components), con el rol de solo lectura `votoscope_web`. Arranque local: `cd web && pnpm install && pnpm dev` (build: `pnpm build`; tests: `pnpm test`). Contrato de datos: [`../docs/db/gold.md`](../docs/db/gold.md).

## Flujo de datos

```
data/raw/  →  bronze.ingestion (registro)  →  silver (normalizado)  →  gold (vistas)  →  web/
```

El ingestador no descarga nada: trabaja sobre los ficheros que haya en `data/raw/`. Excepción acotada: los sondeos de Wikipedia se descargan por CLI (`uv run ingestor fetch-polls`), porque la revisión fija forma parte del contrato del snapshot.

Bronce por proceso: `data/raw/congreso/{código}/` con los 10 `.DAT` (los ZIP originales se quedan en `refs/congreso/`, ver [data-sources.md](data-sources.md)). Bronce de sondeos: `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext` (wikitexto de una revisión fija; lo baja `uv run ingestor fetch-polls`).

## Mapa del repositorio

```
.
├── AGENTS.md                  ← enrutador
├── .agents/                   ← documentación por temas (este directorio)
├── README.md
├── docker-compose.yml         ← Postgres 18 local (host: 5434)
├── data/
│   └── raw/                   ← ficheros fuente (bronce, gitignored)
├── refs/
│   ├── congreso/              ← generales 1986–2023, nivel mesa (referencia local, gitignored) — ver `.agents/data-sources.md`
│   └── ine/                   ← gazetteer INE: CCAA, provincias y municipios en CSV (gitignored) — ver `.agents/data-sources.md`
├── docs/
│   ├── db/schema.drawio       ← ERD de referencia
│   └── ingestor/ingesta.md    ← cómo funciona el ingestador (comandos y carga en silver y gold)
├── ingestor/                  ← ingestador Python (ver ingestor/AGENTS.md)
└── web/                       ← frontend Next.js (ver web/AGENTS.md)
```
