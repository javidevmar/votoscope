# AGENTS.md — ingestor

Contexto del ingestador. Antes de tocar nada, lee también el `AGENTS.md` de la raíz del repo.

## Qué es

Pipeline de datos (Python) que convierte los ficheros electorales descargados en local en tablas normalizadas de PostgreSQL y, más adelante, en las vistas `gold` que consume el frontend. Patrón medallón: bronce (ficheros + registro) → plata (`silver`) → oro (`gold`).

## Ficheros

- **`pyproject.toml`** — proyecto gestionado con uv. Dependencias: SQLAlchemy 2, Alembic, psycopg 3, pydantic-settings.
- **`.env.example`** — variables de entorno; copiar a `.env` para sobrescribir (gitignored).
- **`src/ingestor/settings.py`** — configuración: `DATABASE_URL` (por defecto, el Postgres de docker-compose en `localhost:5433`) y `RAW_DIR` (por defecto, `../data/raw`).
- **`src/ingestor/db.py`** — engine y factoría de sesiones de SQLAlchemy.
- **`src/ingestor/models.py`** — definición del esquema (esquemas `bronze` y `silver`). Borrador pendiente de alinear al ERD: manda `../docs/db/schema.drawio`.
- **`alembic/`** — migraciones. `env.py` toma la URL de `settings.py` (la de `alembic.ini` se deja vacía a propósito).
- **`alembic.ini`** — configuración de Alembic.

## Logging

- Biblioteca estándar (`logging`), sin dependencias extra: un único `configure_logging()` en `src/ingestor/logging.py`, llamado al arrancar cada entrypoint.
- Nivel por entorno: **`LOG_LEVEL`** (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`; por defecto `INFO`).
- Loggers por módulo (`getLogger(__name__)`); formateo perezoso (`logger.info("mesa=%s", m)`, no f-strings); nunca secretos.
- Pendiente de implementar (va con el primer entrypoint del pipeline).

## Dependencias

- **Ninguna dependencia nueva sin consentimiento explícito del usuario** (ver [`../.agents/conventions.md`](../.agents/conventions.md)). Primero se propone y se espera respuesta; se instalan con `uv add`.

## Flujo de trabajo del esquema

1. Editar `src/ingestor/models.py`.
2. `uv run alembic revision --autogenerate -m "descripción corta"`.
3. Revisar la migración generada y añadir los `CREATE SCHEMA IF NOT EXISTS` a mano (autogenerate no los genera).
4. `uv run alembic upgrade head`.
5. `uv run alembic check` — debe reportar que no hay diferencias (sin drift).
6. Reflejar el cambio en `../docs/db/schema.drawio`: siempre ERD ↔ modelos ↔ migración.

Nunca: DDL a mano, SQL de inicialización, editar una migración ya aplicada.

## Comandos

- `uv sync` — instalar dependencias.
- `uv run alembic upgrade head` — aplicar migraciones.
- `uv run alembic revision --autogenerate -m "…"` — nueva migración desde los modelos.
- `uv run alembic check` — verificar que no hay drift.

La base de datos se levanta desde la raíz del repo: `docker compose up -d --wait`.

## Datos

- Ficheros fuente: `../data/raw/` (no versionados; nunca se modifican).
- Cada fichero ingerido queda registrado en `bronze.ingesta` con su sha256.

## Pendiente

- Alinear `models.py` al ERD y generar la migración inicial (`alembic/versions/` está vacío).
- Loader bronce → plata.
- Vistas `gold`.
