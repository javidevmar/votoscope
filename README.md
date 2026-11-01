# Votoscope

Agregador de resultados electorales de España.

## Qué es

Votoscope convierte los resultados que publica el Ministerio del Interior en
datos normalizados consultables. MVP: las últimas elecciones generales
(Congreso), con resultados por mesa. Pipeline bronce → plata → oro (esquemas
`silver` y `gold`) en [`ingestor/`](ingestor/) (Python, PostgreSQL) y una web
Next.js que lee `gold` en servidor. `data/raw/` (bronce) no se versiona.

## Requisitos

- Docker (con Compose)
- uv
- Python 3.12 o superior (lo gestiona uv)

## Puesta en marcha

1. Base de datos (Postgres 18 en `localhost:5434`):

   ```sh
   docker compose up -d --wait
   ```

2. Ingestador:

   ```sh
   cd ingestor
   uv sync
   uv run alembic upgrade head
   ```

3. Verificación:

   ```sh
   uv run pytest
   ```

   Para sobrescribir configuración: copiar
   [`ingestor/.env.example`](ingestor/.env.example) a `ingestor/.env`.

## Datos

- Resultados (portal infoelectoral → `data/raw/congreso/{código}/`, no
  versionado): descargar el ZIP MESA del proceso y descomprimirlo (detalle en
  [`.agents/data-sources.md`](.agents/data-sources.md)).
- Gazetteer INE → `refs/ine/`.
- Carga:

  ```sh
  uv run ingestor load-geography
  uv run ingestor ingest ../data/raw/congreso
  uv run ingestor fetch-polls
  uv run ingestor ingest-polls
  ```

## Web

- `cd web && pnpm install && pnpm dev` (http://localhost:3000); build con
  `pnpm build`, tests con `pnpm test`. Lee las vistas `gold` en servidor a
  través del BFF de `web/app/api/`. Ver [`web/AGENTS.md`](web/AGENTS.md).

## Documentación

- [`AGENTS.md`](AGENTS.md) — índice del repo y enrutador de la documentación.
- [`.agents/`](.agents/) — docs de contexto: arquitectura, modelo de datos,
  fuentes, convenciones y entorno.
- [`docs/ingestor/ingesta.md`](docs/ingestor/ingesta.md) — comandos y carga.
- [`docs/db/schema.drawio`](docs/db/schema.drawio) — ERD.
- [`specs/`](specs/) — specs por feature.

## Fuentes y atribución

- **Resultados electorales**: portal infoelectoral del Ministerio del Interior
  ([infoelectoral.interior.gob.es](https://infoelectoral.interior.gob.es));
  los ficheros `.DAT` cargados son copias locales de sus descargas.
- **Sondeos**: página «Opinion polling for the 2026 Spanish general election»
  de Wikipedia (en), reutilizada bajo licencia **CC BY-SA**; revisión usada:
  [1380859635](https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid=1380859635).
  Cada snapshot guarda su `revision_id` y cada carga se verifica en
  [`docs/ingestor/polls-run.md`](docs/ingestor/polls-run.md).
