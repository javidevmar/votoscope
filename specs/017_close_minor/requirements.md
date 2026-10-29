# Requisitos — `close_minor`

Feature `id 17` de [`feature_list.json`](../../feature_list.json). Alcance: el cierre del repositorio. Tres entregables: el **README** (qué es el proyecto y cómo levantarlo), la **atribución de las fuentes** (portal infoelectoral y sondeos de Wikipedia CC BY-SA con enlace a la revisión) y la **pasada final de estado y coherencia** (`.agents/status.md` y documentos de contexto).

Esta feature **no añade código de aplicación**: sus artefactos son documentos (README, `.agents/status.md`, docs de contexto y ejemplos de configuración) y los tests que los verifican. Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Sin dependencias nuevas. Sin excepciones nuevas. El README se escribe en español —idioma de los docs ([`.agents/conventions.md`](../../.agents/conventions.md))—; identificadores y comandos, tal cual.

El texto concreto lo redacta el implementer; el spec fija **qué debe documentarse y los anclajes verificables** (subcadenas y enlaces), no el texto completo. Lo que cambia solo (la revisión de Wikipedia usada, los recuentos) no se congela: el enlace a la revisión se actualiza a la realmente usada.

## R1

El README DEBE describir qué es Votoscope: agregador de resultados electorales de España; MVP de las últimas elecciones generales (Congreso) con resultados por mesa; pipeline bronce → plata → oro (esquemas `silver` y `gold`) del ingestador Python y web Next.js que lee `gold` en servidor.

## R2

El README DEBE listar los requisitos previos para levantar el proyecto: Docker con Compose, `uv` y Python 3.12 o superior.

## R3

El README DEBE documentar la puesta en marcha del entorno local con los comandos, en orden: `docker compose up -d --wait` (Postgres 18 en `localhost:5434`), `cd ingestor`, `uv sync`, `uv run alembic upgrade head` y la verificación `uv run pytest`.

## R4

El README DEBE explicar el origen local de los datos no versionados (resultados descargados a mano del portal infoelectoral a `data/raw/congreso/{código}/`; gazetteer INE en `refs/ine/`) y los comandos de carga `uv run ingestor load-geography`, `uv run ingestor ingest <ruta>`, `uv run ingestor fetch-polls` y `uv run ingestor ingest-polls`.

## R5

DONDE `web/` contenga la aplicación Next.js scaffoldada (feature 16), el README DEBE documentar cómo levantarla (comando de desarrollo del scaffold) y que los datos se leen de las vistas `gold` de PostgreSQL en servidor.

## R6

El README DEBE atribuir los resultados electorales a su fuente primaria: el portal infoelectoral del Ministerio del Interior (`infoelectoral.interior.gob.es`).

## R7

El README DEBE atribuir los sondeos a Wikipedia indicando la página de sondeos, la licencia CC BY-SA y el enlace a la revisión usada (`oldid`).

## R8

El README DEBE enlazar la documentación de contexto: el índice [`AGENTS.md`](../../AGENTS.md) (con [`.agents/`](../../.agents/)) y [`docs/ingestor/ingesta.md`](../../docs/ingestor/ingesta.md).

## R9

Todos los enlaces relativos del README DEBEN resolver a rutas existentes del repositorio.

## R10

`.agents/status.md` DEBE reflejar el estado final tras la entrega: fecha de actualización, las features 15–17 (vistas `gold`, web y README/atribución) en «Hecho» y la cola pendiente apuntando a [`feature_list.json`](../../feature_list.json) con la feature 18 `source_norm`.

## R11

Los documentos de contexto (`.agents/architecture.md`, `.agents/environment.md`, `ingestor/AGENTS.md` y `web/AGENTS.md`) NO DEBEN contener afirmaciones obsoletas sobre piezas ya entregadas: «Pendiente de scaffold», «Pendientes de crear», «Aún no hay scaffold», las vistas `gold` como trabajo pendiente ni el logging «pendiente en la web».

## R12

Las referencias al puerto del Postgres local DEBEN ser `5434` —no `5433`— en el README, `.agents/architecture.md`, `ingestor/.env.example` y el comentario de `docker-compose.yml`.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «README con qué es el proyecto y cómo levantarlo» | R1, R2, R3, R4, R5; enlaces: R8, R9 |
| «atribución de la fuente infoelectoral y de Wikipedia (CC BY-SA, enlace a la revisión)» | R6, R7 |
| «.agents/status.md y documentos de contexto al día» | R10, R11; coherencia de puerto detectada al redactar: R12 |

## Nota de verificación

- R1–R12: `ingestor/tests/test_close_minor.py` — tests que leen ficheros del repositorio (solo lectura; sin red y sin base de datos).
- R5 se salta si `web/package.json` no existe (la sección web del README es condicional a que la feature 16 esté entregada; el orden de la cola la ejecuta antes que esta).
- Esta feature no toca `docs/ingestor/polls-run.md` ni la sección «Sondeos (Wikipedia)» de `.agents/data-sources.md`: la revisión de Wikipedia que cite el README sale de lo ya documentado ahí.
