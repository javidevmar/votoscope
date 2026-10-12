# Convenciones

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). El estilo de código está en [`style.md`](style.md).

## Base de datos

- Tablas y columnas en **inglés**, con el vocabulario del dominio (election, polling_station, census…). ERD, modelos y migración siguen el modelo v2.
- PK sustitutas en todas las tablas: `id` entero autoincremental; los códigos naturales van aparte con `UNIQUE` (`ine_code`, `slug`, `(election_id, code)`, `(polling_station_id, election_id)`…). No se usan `uuid`.
- Claves ajenas: `<tabla>_id` (polling_station_id, election_id…).
- Agregados y porcentajes solo en `gold`; `silver` guarda hechos.
- `data/raw/` es inmutable y no se versiona.

## Idioma

- Identificadores de código: inglés.
- Documentación de trabajo (este directorio y los AGENTS.md): español.

## Logging

- Ambas partes (ingestador y web) registran logs con niveles estándar: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- El nivel se fija por variable de entorno: **`LOG_LEVEL`** (por defecto `INFO`). Nunca hardcodeado.
- Ingestador: biblioteca estándar (`logging`), sin dependencias extra; un único `configure_logging()` que arranca cada entrypoint; formato único (fecha · nivel · logger · mensaje); loggers por módulo (`getLogger(__name__)`).
- Web: misma convención de niveles; `LOG_LEVEL` en servidor (`NEXT_PUBLIC_LOG_LEVEL` solo si hiciera falta en cliente).
- Nunca se loguean secretos.

## Dependencias

- **Ninguna dependencia nueva se añade sin consentimiento explícito del usuario**: primero se propone (problema que resuelve, por qué no basta la stdlib o lo ya instalado) y se espera respuesta.
- Solo si aporta de verdad y es utilizable (mantenida, compatible, sin duplicar lo existente).
- Instalación con el gestor del proyecto: `uv add` en el ingestador; en la web, el gestor que se fije al hacer el scaffold.
- Ya aprobadas (ingestador): SQLAlchemy, Alembic, psycopg, pydantic-settings.

## Tests

- **TDD** para la lógica (parsers, loader, transformaciones): primero el test que falla, luego el código mínimo, luego refactor.
- Framework: **pytest** (dev-dependency aprobada); los tests del ingestador viven en `ingestor/tests/`.
- CI: diferida; se montará cuando exista el loader.
- Estrategia de tests de la web: se decidirá en su scaffold.
