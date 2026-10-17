# Requisitos — `polls_schedule`

Feature `id 10` de [`feature_list.json`](../../feature_list.json); tarea 6 del plan [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), §«Ejecución periódica (2×/día)». Alcance: el job que sincroniza los sondeos cada 12 h —la entrada de cron/launchd documentada para el Postgres local y el esqueleto del workflow programado para cuando exista entorno de despliegue— y los tests del camino «sin novedades» del ciclo completo.

El ciclo es el encadenado de los dos comandos ya existentes (features 6 y 9): `uv run ingestor fetch-polls` y, solo si termina con éxito, `uv run ingestor ingest-polls`; es la interfaz fijada en [`specs/009_polls_load/design.md`](../009_polls_load/design.md) §«Interfaz para las features 10–11». Esta feature **no añade código de producción**: su contrato son los artefactos (documentación y workflow) y los tests que fijan el comportamiento del ciclo sin novedades.

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Sin dependencias nuevas. Sin excepciones nuevas: los fallos ya los propaga `IngestError` (features 6 y 9).

## R1

El sistema DEBE documentar en `.agents/environment.md` el job de sincronización de sondeos cada 12 h —los dos comandos encadenados, ejecutados desde `ingestor/` contra el Postgres local— y el significado de su exit code (`0` = sincronizado o sin novedades; distinto de `0` = error con el mensaje en el log).

## R2

El sistema DEBE incluir en `.agents/environment.md` la entrada de crontab lista para copiar (cadencia `0 6,18 * * *`, rutas absolutas del repositorio y de `uv`, salida redirigida a `data/polls-sync.log`) y la alternativa de launchd en macOS.

## R3

El sistema DEBE indicar en `.agents/environment.md` que el job local es provisional mientras el destino sea el Postgres de docker-compose y que, cuando exista entorno de despliegue, pasa al workflow programado [`.github/workflows/polls-sync.yml`](../../.github/workflows/polls-sync.yml).

## R4

El sistema DEBE incluir `.github/workflows/polls-sync.yml` con un disparador `schedule:` de cadencia 12 h (`0 6,18 * * *`) y `workflow_dispatch`.

## R5

MIENTRAS no exista entorno de despliegue, `polls-sync.yml` DEBE limitarse a un job placeholder que registre por log el mecanismo actual (cron/launchd local) y el comando que ejecutará, y que termine con exit 0 sin tocar ninguna base de datos.

## R6

CUANDO la revisión resuelta ya está en disco como `{revid}.wikitext`, el sistema DEBE resolverla con una única petición HTTP —la de resolución de la revisión— y terminar `fetch-polls` con exit code 0.

## R7

MIENTRAS la revisión resuelta ya esté en disco, `fetch-polls` NO DEBE descargar ni reescribir el fichero del snapshot.

## R8

CUANDO todos los snapshots bajo `RAW_DIR/polls` están `processed`, el sistema DEBE terminar `ingest-polls` con exit code 0.

## R9

CUANDO todos los snapshots están `processed`, `ingest-polls` NO DEBE añadir filas a `bronze.ingestion` ni modificar las filas de `poll`, `poll_result`, `pollster` o `party`.

## R10

El sistema DEBE ejecutar el pase de resolución de elecciones de `ingest-polls` también cuando no hay snapshots pendientes, de modo que los sondeos con `election_id` nulo queden enlazados en la siguiente ejecución del ciclo (≤12 h).

## R11

SI la API no devuelve ninguna revisión para la página (ausente o renombrada sin redirección) ENTONCES el sistema DEBE terminar el ciclo con exit code distinto de `0` y registrar el error por log.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «entrada de cron/launchd documentada en `.agents/environment.md` (mientras el destino sea el Postgres local)» | R1, R2, R3 |
| «esqueleto de workflow con `schedule:` para cuando exista entorno de despliegue» | R4, R5 |
| «test del camino «sin novedades»: no descarga, exit 0» | R6, R7, R8, R9, R10 |
| Extra (plan §«Ejecución periódica»): «página ausente o renombrada → exit ≠ 0 y log» | R11 |

## Nota de verificación

- R6–R11: `ingestor/tests/test_polls_schedule.py`, con el transporte HTTP inyectado (fake opener sobre `ingestor.polls.fetch.urlopen`) y las fixtures reales de la API (`api_revision.json`, `api_missing.json`); ningún test usa red. El ciclo se ejercita con `cli.main(["fetch-polls"])` y `cli.main(["ingest-polls"])`.
- R8–R10: con la fixture `db` de `ingestor/tests/conftest.py` (esquemas Postgres de test; `pytest.skip` si no hay Postgres).
- R1–R5: tests que leen `.agents/environment.md` y `.github/workflows/polls-sync.yml` y comprueban las subcadenas acordadas en [`design.md`](design.md) §Documentación.
