# AGENTS.md — ingestor

Contexto del ingestador. Antes de tocar nada, lee también el `AGENTS.md` de la raíz del repo.

Proceso: toda feature con `sdd: true` en [`../feature_list.json`](../feature_list.json) pasa por su spec en `../specs/<name>/` antes de tocar código; ver [`../AGENTS.md`](../AGENTS.md) y [`../.agents/specs.md`](../.agents/specs.md).

## Qué es

Pipeline de datos (Python) que convierte los ficheros electorales descargados en local en tablas normalizadas de PostgreSQL y, más adelante, en las vistas `gold` que consume el frontend. Patrón medallón: bronce (ficheros + registro) → plata (`silver`) → oro (`gold`).

Los datos electorales se siguen descargando a mano; los sondeos de Wikipedia se descargan por CLI (`fetch-polls`) porque la revisión fija es parte del contrato del snapshot.

## Documentación

- Cómo funciona el ingestador (comandos, comportamiento y carga en `silver`): [`../docs/ingestor/ingesta.md`](../docs/ingestor/ingesta.md).
- **Todo cambio que afecte a cómo funciona** (CLI, flujo de ingesta, validaciones, geografía o lo que acaba en `silver`) **revisa y actualiza esa documentación en el mismo commit.**

## Ficheros

- **`pyproject.toml`** — proyecto gestionado con uv. Dependencias: SQLAlchemy 2, Alembic, psycopg 3, pydantic-settings; dev: pytest, ruff. Script de consola: `ingestor`.
- **`.env.example`** — variables de entorno; copiar a `.env` para sobrescribir (gitignored).
- **`src/ingestor/settings.py`** — configuración: `DATABASE_URL` (por defecto, el Postgres de docker-compose en `localhost:5434`), `RAW_DIR` (por defecto, `../data/raw`) e `INE_DIR` (por defecto, `../refs/ine`).
- **`src/ingestor/db.py`** — engine y factoría de sesiones de SQLAlchemy.
- **`src/ingestor/models.py`** — definición del esquema, modelo v2 (inglés; esquemas `bronze` y `silver`; PK natural INE en `autonomous_community`/`province`).
- **`src/ingestor/elections/`** — dominio de elecciones (ficheros del ministerio):
  - `parsers/` — longitud fija, agnóstica al proceso: un módulo por fichero (`file02`, `file03`, `file05`, `file09`, `file10`) y helpers en `common.py`.
  - `adapters/` — reglas por proceso electoral; registro por código (`congreso.py` para el 02; Senado/autonómicas/municipales añadirán módulo propio).
  - `loaders/` — persistencia: `geography.py` (`load-geography`), `election.py` (bronce + plata de una elección).
- **`src/ingestor/polls/`** — dominio de sondeos: `fetch.py` (descarga del snapshot: resuelve la revisión actual vía API y baja su wikitexto a `data/raw/polls/`; solo `urllib` de la stdlib).
- **`src/ingestor/cli.py`** / **`logging.py`** — entrypoints (`ingestor load-geography`, `ingestor ingest <ruta>`, `ingestor fetch-polls`) y `configure_logging()`.
- **`alembic/`** — migraciones; `2a1c9e836128` (inicial, regenerada con la PK natural INE) y `06a250c36252` (`municipality.name` nullable), aplicadas en local. `env.py` toma la URL de `settings.py` (la de `alembic.ini` se deja vacía a propósito).
- **`alembic.ini`** — configuración de Alembic.
- **`tests/`** — pytest; `tests/fixtures/` con recortes reales mínimos (sin red ni `refs/`).

## Logging

- Biblioteca estándar (`logging`), sin dependencias extra: un único `configure_logging()` en `src/ingestor/logging.py`, llamado al arrancar cada entrypoint.
- Nivel por entorno: **`LOG_LEVEL`** (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`; por defecto `INFO`).
- Loggers por módulo (`getLogger(__name__)`); formateo perezoso (`logger.info("mesa=%s", m)`, no f-strings); nunca secretos.

## Tests

- **TDD con pytest**; los tests viven en `tests/`. Prioridad: parsers de los ficheros de entrada y reglas del adaptador.
- Fixtures de los parsers: `tests/fixtures/` (recortes reales mínimos + casos sintéticos); los tests no dependen de `refs/` ni de la red.

## Dependencias

- **Ninguna dependencia nueva sin consentimiento explícito del usuario** (ver [`../.agents/conventions.md`](../.agents/conventions.md)). Primero se propone y se espera respuesta; se instalan con `uv add`.
- Aprobadas (runtime): SQLAlchemy, Alembic, psycopg, pydantic-settings. Dev: pytest, ruff.

## Ingesta (bronce → plata)

- **Comandos**: `uv run ingestor load-geography` (gazetteer INE → `silver`) y `uv run ingestor ingest <ruta>` (una carpeta de elección o una raíz con varias; `--force` recarga aunque todo esté procesado).
- **Bronce**: cada fichero leído (02, 03, 09, 10 y 05 si existe) se registra en `bronze.ingestion` con ruta relativa a `data/raw/` y sha256; estados `registered` → `processed` | `failed`. Si todos los ficheros de una elección ya están `processed`, la elección se salta.
- **Recarga**: si algún fichero es nuevo, se borran los hechos (`vote`, `turnout`) y candidaturas (`party_election`) de esa elección y se recargan todos sus ficheros en una transacción.
- **Validaciones**: candidaturas de 10 ⊆ 03; mesas de 10 ⊆ 09; suma de votos de 10 == campo «votos a candidaturas» de 09 por mesa. Esta última se degrada a warning en los procesos donde los propios ficheros del ministerio no cuadran (años en `RELAXED_STATION_TOTALS` del adaptador; detalle en [`../.agents/data-sources.md`](../.agents/data-sources.md)).
- **Geografía**: `load-geography` es idempotente y actualiza nombres desde `refs/ine/`; la ingesta crea los pseudo-municipios CERA (`<provincia>999`) y los municipios que ya no existen (nombre del 05 de su elección, o null con warning).
- **Adaptadores**: un módulo por proceso en `elections/adapters/`; el registro despacha por el código de proceso del fichero 02 (Congreso = `02`).

1. Editar `src/ingestor/models.py`.
2. `uv run alembic revision --autogenerate -m "descripción corta"`.
3. Revisar la migración generada y añadir los `CREATE SCHEMA IF NOT EXISTS` a mano (autogenerate no los genera).
4. `uv run alembic upgrade head`.
5. `uv run alembic check` — debe reportar que no hay diferencias (sin drift).
6. Reflejar el cambio en `../docs/db/schema.drawio`: siempre ERD ↔ modelos ↔ migración.

Nunca: DDL a mano, SQL de inicialización, editar una migración ya aplicada (salvo si no se aplicó nunca en producción).

## Comandos

- `uv sync` — instalar dependencias.
- `uv run alembic upgrade head` — aplicar migraciones.
- `uv run alembic revision --autogenerate -m "…"` — nueva migración desde los modelos.
- `uv run alembic check` — verificar que no hay drift.
- `uv run ingestor load-geography` — cargar el gazetteer INE (`refs/ine/`) en `silver`.
- `uv run ingestor ingest <ruta>` — ingerir una carpeta de elección o una raíz con varias (las ya procesadas se saltan por sha256; `--force` recarga).
- `uv run ingestor fetch-polls [--page <título>]` — descargar el snapshot de revisión fija de la página de sondeos a `data/raw/polls/wikipedia-en/` (sin novedades = una sola llamada a la API).
- `uv run pytest` / `uv run ruff check .` — tests y lint.

La base de datos se levanta desde la raíz del repo: `docker compose up -d --wait`.

## Datos

- Ficheros fuente: `../data/raw/` (no versionados; nunca se modifican); bronce por proceso en `data/raw/congreso/{código}/`.
- Cada fichero ingerido queda registrado en `bronze.ingestion` con su sha256.

## Pendiente

- Vistas `gold`.
