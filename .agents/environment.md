# Entorno de desarrollo

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Base de datos

- **Postgres 18** en Docker, definido en `docker-compose.yml` (raíz del repo).
- Levantar: `docker compose up -d --wait`. Parar y borrar datos: `docker compose down -v`.
- Puerto host: **5433** (el 5432 de la máquina está ocupado por un Postgres local).
- Usuario, clave y base de datos: `votoscope`.
- El volumen `pgdata` se monta en `/var/lib/postgresql` (Postgres 18 cambió el punto de montaje recomendado; no volver a `/var/lib/postgresql/data`).

## Ingestador

- Python gestionado con **uv**. Detalles y comandos: [`../ingestor/AGENTS.md`](../ingestor/AGENTS.md).
- Variables de entorno: `ingestor/.env.example` (`DATABASE_URL` apunta al contenedor).
- Logs: `LOG_LEVEL` fija el nivel en ambas partes (por defecto `INFO`; ver [conventions.md](conventions.md)).

## Frontend

- Pendiente de scaffold. Ver [`../web/AGENTS.md`](../web/AGENTS.md).
