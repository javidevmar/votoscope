# Entorno de desarrollo

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Base de datos

- **Postgres 18** en Docker, definido en `docker-compose.yml` (raíz del repo).
- Levantar: `docker compose up -d --wait`. Parar y borrar datos: `docker compose down -v`.
- Puerto host: **5434** (el 5432 de la máquina está ocupado por un Postgres local).
- Usuario, clave y base de datos: `votoscope`.
- El volumen `pgdata` se monta en `/var/lib/postgresql` (Postgres 18 cambió el punto de montaje recomendado; no volver a `/var/lib/postgresql/data`).

## Ingestador

- Python gestionado con **uv**. Detalles y comandos: [`../ingestor/AGENTS.md`](../ingestor/AGENTS.md).
- Variables de entorno: `ingestor/.env.example` (`DATABASE_URL` apunta al contenedor).
- Logs: `LOG_LEVEL` fija el nivel en ambas partes (por defecto `INFO`; ver [conventions.md](conventions.md)).

## Sincronización de sondeos (2×/día)

Mientras el destino sea el Postgres local (docker-compose), el job que sincroniza los sondeos cada 12 h es una entrada de **crontab** que encadena los dos comandos:

```crontab
# Sondeos (Wikipedia): cada 12 h (06:00 y 18:00 locales); `crontab -e` para instalarla.
0 6,18 * * * cd /Users/javier/Developer/1poller/ingestor && { /opt/homebrew/bin/uv run ingestor fetch-polls && /opt/homebrew/bin/uv run ingestor ingest-polls; } >> /Users/javier/Developer/1poller/data/polls-sync.log 2>&1
```

- Sin novedades el ciclo es una única llamada ligera a la API y termina con exit 0 sin escribir nada (salvo el pase de resolución de elección, que corre igual).
- Exit code: `0` = sincronizado o sin novedades; distinto de 0 = error (página ausente o renombrada, red caída, Postgres parado) y el mensaje queda en `data/polls-sync.log`. El `&&` evita que `ingest-polls` corra si el fetch falló.
- Las llaves `{ …; }` agrupan la cadena para que `>>` y `2>&1` cubran también la salida de `fetch-polls`: sin ellas la redirección solo aplicaría al último comando.
- Rutas absolutas a propósito: cron no hereda el `PATH` del shell (`/opt/homebrew/bin/uv` es el `command -v uv` de este Mac) y `uv run` necesita el directorio del proyecto (`cd ingestor`), que es donde `settings` lee `ingestor/.env`.
- Alternativa **launchd** (macOS): un agente con `StartCalendarInterval` y el mismo comando, si el Mac duerme a las horas del cron.
- El job es provisional: cuando exista entorno de despliegue pasa al workflow programado [`../.github/workflows/polls-sync.yml`](../.github/workflows/polls-sync.yml) (esqueleto ya en el repo).

## Frontend

- Pendiente de scaffold. Ver [`../web/AGENTS.md`](../web/AGENTS.md).
