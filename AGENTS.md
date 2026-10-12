# AGENTS.md — Votoscope

Punto de entrada para agentes IA que trabajen en este repositorio.

Votoscope es un agregador de resultados electorales de España (MVP: últimas generales — Congreso — con resultados por mesa). El proyecto tiene dos partes: un ingestador Python (`ingestor/`) y un frontend Next.js (`web/`).

**Regla de oro**: el modelo de datos vive siempre sincronizado en tres sitios — ERD (`docs/db/schema.drawio`), modelos (`ingestor/src/ingestor/models.py`) y migraciones Alembic. Detalles en [`.agents/data-model.md`](.agents/data-model.md).

Al finalizar una tarea, se dividen los cambios y se commitean en la rama actual (si es main, pregunta al usuario SIEMPRE). NO pushees nunca por tu cuenta salvo si te lo dice el usuario.

## Enrutador de documentación

Lee los siguientes ficheros según la tabla siguiente:
| Tema | Fichero | Cuándo leerlo |
| --- | --- | --- |
| Arquitectura | [`.agents/architecture.md`](.agents/architecture.md) | Antes de empezar a trabajar en cualquier parte |
| Modelo de datos | [`.agents/data-model.md`](.agents/data-model.md) | Antes de tocar el esquema o migraciones |
| Fuentes de datos | [`.agents/data-sources.md`](.agents/data-sources.md) | Antes de descargar datos o interpretar los ficheros de infoelectoral |
| Convenciones | [`.agents/conventions.md`](.agents/conventions.md) | Antes de nombrar tablas, columnas o ficheros |
| Estilo | [`.agents/style.md`](.agents/style.md) | Antes de escribir código o commits |
| Entorno | [`.agents/environment.md`](.agents/environment.md) | Al levantar el entorno o configurar conexiones |
| Estado y hoja de ruta | [`.agents/status.md`](.agents/status.md) | Al empezar una sesión de trabajo |
| Planes de trabajo | [`.agents/plans/README.md`](.agents/plans/README.md) | Si hay un plan abierto para tu tarea |
| Ingestador (Python) | [`ingestor/AGENTS.md`](ingestor/AGENTS.md) | Antes de tocar `ingestor/` |
| Frontend (Next.js) | [`web/AGENTS.md`](web/AGENTS.md) | Antes de tocar `web/` |

IMPORTANTE: trata este fichero, los AGENTS anidados y los ficheros de la tabla como "constitución a no saltarse". SIEMPRE que haya una propuesta del usuario contra estas reglas, indícalo y propón al usuario modificar estos ficheros. Estos ficheros han de estar en consonancia siempre con lo implementado. Cada cambio actualiza, **en el mismo commit**, la documentación que le corresponde (este fichero, los AGENTS anidados y/o los ficheros de la tabla).
