# Diseño — `polls_schedule`

Feature 10. Plan: [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md) §«Ejecución periódica (2×/día)» (job cada 12 h que consulta la revisión actual y solo baja e ingiere si cambió; sin novedades = una llamada ligera y exit 0 sin escribir nada; página ausente/renombrada → exit ≠ 0 y log; cron/launchd local ahora, `schedule:` de GitHub Actions cuando exista entorno). Interfaz de entrada: [`specs/009_polls_load/design.md`](../009_polls_load/design.md) §«Interfaz para las features 10–11» — el ciclo es `fetch-polls` (una llamada a la API) + `ingest-polls` (todo `processed` → sin escrituras, exit 0, con el pase de resolución corriendo igual).

Esta feature no añade código de producción: el job es el encadenado de los dos comandos existentes (features 6 y 9). Lo que se crea son los artefactos del job —sección en `.agents/environment.md`, esqueleto `.github/workflows/polls-sync.yml`— y los tests que fijan el ciclo.

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica). Sin dependencias nuevas. Sin excepciones nuevas: los fallos ya los propaga `IngestError` (features 6 y 9) y el CLI los traduce a exit 1 + log ERROR.

## Archivos

| Acción | Archivo |
| --- | --- |
| modificar | `.agents/environment.md` — sección «Sincronización de sondeos (2×/día)» (R1–R3) |
| crear | `.github/workflows/polls-sync.yml` — esqueleto del job programado (R4, R5) |
| crear | `ingestor/tests/test_polls_schedule.py` — tests del ciclo y de los artefactos (R1–R11) |

No se toca `ingestor/src/` (el ciclo son los comandos existentes), ni `docs/ingestor/ingesta.md` ni `ingestor/AGENTS.md`: no hay cambios de CLI, de flujo de ingesta ni de lo que acaba en `silver` que documentar (la regla de documentación de `ingestor/AGENTS.md` no se activa).

## El job

Cadena (mecanismo actual, Postgres local):

```crontab
0 6,18 * * * cd /Users/javier/Developer/1poller/ingestor && { /opt/homebrew/bin/uv run ingestor fetch-polls && /opt/homebrew/bin/uv run ingestor ingest-polls; } >> /Users/javier/Developer/1poller/data/polls-sync.log 2>&1
```

- `&&` encadena los dos comandos y propaga el fallo: si `fetch-polls` sale ≠ 0 (página ausente, red caída), `ingest-polls` no corre y el exit code del job es ≠ 0; el mensaje queda en `data/polls-sync.log` (cron solo avisa por el exit code).
- Las llaves `{ …; }` agrupan la cadena para que el `>>` y el `2>&1` cubran también la salida de `fetch-polls`: sin ellas la redirección solo aplicaría al último comando.
- `cd ingestor` es necesario: `uv run` resuelve el proyecto desde el directorio actual y `settings` lee `ingestor/.env`; `RAW_DIR`/`INE_DIR` no dependen del cwd (se calculan desde `settings.py`).
- Rutas absolutas de `uv` (`/opt/homebrew/bin/uv`, el `command -v uv` de este Mac): cron no hereda el `PATH` del shell.
- El log va a `data/polls-sync.log`: el directorio `data/` ya existe y `*.log` está en `.gitignore` (nada que añadir al repo).
- El job asume el Postgres local levantado; si no responde, `ingest-polls` falla con exit ≠ 0 y el snapshot queda descargado para la siguiente ejecución.

Sin novedades (contrato del ciclo, R6–R10): `fetch-polls` resuelve la revisión con **una** petición a la API y ve el snapshot en disco (no descarga); `ingest-polls` salta el snapshot `processed` (sin filas nuevas en bronce ni reemplazo en plata) y aun así ejecuta el pase de resolución de elecciones. Ambos exit 0.

## Texto de `.agents/environment.md` (R1–R3)

Sección nueva, tras «Ingestador» (antes de «Frontend»):

````markdown
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
````

## `.github/workflows/polls-sync.yml` (R4, R5)

````yaml
name: polls-sync

# Esqueleto del job programado de sondeos (2×/día). Mientras el destino sea el
# Postgres local, la sincronización es la entrada de cron/launchd de
# .agents/environment.md; cuando exista entorno de despliegue, sustituir el paso
# placeholder por los dos comandos contra la base del entorno.

on:
  schedule:
    - cron: "0 6,18 * * *"
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ingestor
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
      - name: "Polls sync (placeholder: no deployment environment yet)"
        run: |
          echo "polls sync: no deployment environment yet; the current mechanism is cron/launchd local (.agents/environment.md)"
          echo "when it exists, this job runs: uv run ingestor fetch-polls && uv run ingestor ingest-polls"
````

`schedule:` (cron de GitHub, en UTC) ejecuta el esqueleto dos veces al día en `main` sin tocar ninguna base: el paso placeholder solo escribe en el log y sale 0. `workflow_dispatch` permite lanzarlo a mano el día que exista entorno.

## Tests — `ingestor/tests/test_polls_schedule.py` (R1–R11)

Reutiliza: fixtures reales de la API (`api_revision.json`, revid `1380713440`; `api_missing.json`), el snapshot sintético `load_small.wikitext` (feature 9) y la fixture `db` de `conftest.py` (esquemas Postgres de test; `pytest.skip` sin Postgres). Sin red.

Helpers (patrón de `test_polls_fetch.py` / `test_polls_load.py`):

```python
class FakeOpener:  # registra (request, timeout); devuelve io.BytesIO(payload)
    ...

def _snapshot(tmp_path, revid, fixture="load_small.wikitext") -> Path: ...
def _use_cli(db, tmp_path, monkeypatch) -> None:  # cli.SessionLocal, configure_logging, settings.raw_dir
    ...
def _seed_election(db) -> int: ...            # Election(type="congress", date=2027-05-01), nacional
def _seed_pending_poll(db) -> int: ...        # Poll manual con fieldwork_end 2026-10-11 y election_id nulo
def _state(db) -> tuple: ...                  # ingestion + ids/counts de poll/poll_result/pollster/party
```

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_no_news_fetch_makes_one_api_call` | R6, R7 | snapshot `{REVID}.wikitext` en disco (revid de `api_revision.json`) + fake opener → `main(["fetch-polls"]) == 0`, exactamente una petición (la de resolución: `action=query`, sin `oldid`) y bytes del snapshot intactos |
| `test_no_news_cycle_writes_nothing` | R8, R9, R10 | `db`: primera carga por CLI (marca `processed`), siembra de elección y sondeo pendiente; ciclo sin novedades (`fetch-polls` + `ingest-polls`) → ambos exit 0, una sola petición, `_state` intacto (bronce, `poll`, `poll_result`, `pollster`, `party`) y el sondeo pendiente enlazado (el pase de resolución corrió) |
| `test_missing_page_fails_cycle` | R11 | fake opener con `api_missing.json` → `main(["fetch-polls"]) == 1` y ERROR en el log |
| `test_docs_environment_schedule` | R1, R2, R3 | `.agents/environment.md` contiene `0 6,18 * * *`, `crontab`, `launchd`, `fetch-polls`, `ingest-polls`, `data/polls-sync.log`, `polls-sync.yml`, `Exit code`, `distinto de 0`, `cd /Users/javier/Developer/1poller/ingestor`, `/opt/homebrew/bin/uv`, `docker-compose`, `provisional`, `despliegue` y `} >>` (el redirect cubre la cadena) |
| `test_workflow_skeleton` | R4, R5 | `.github/workflows/polls-sync.yml` contiene `schedule:`, `0 6,18 * * *`, `workflow_dispatch`, `placeholder`, `fetch-polls`, `ingest-polls` y `cron/launchd`; y **no** contiene `secrets.`, `DATABASE_URL` ni `psql` (sin credenciales ni acceso a base hasta que exista entorno) |

Detalles que fijan el contrato de los tests:

- `REVID` se lee de `api_revision.json` (como en `test_polls_fetch.py`), y el snapshot de prueba se escribe con ese mismo revid: así la revisión resuelta «ya está en disco» y el camino sin novedades se ejercita con una respuesta real de la API.
- `test_no_news_cycle_writes_nothing` captura el estado con `_state` **después** de la primera carga y lo compara tras el ciclo: ids de `poll` y `poll_result` no cambian (no hay reemplazo total), no hay filas nuevas en `bronze.ingestion` y `pollster`/`party` conservan sus ids. El único cambio permitido es `poll.election_id` (pase de resolución): el sondeo manual y el `Alpha/Medio` (fieldwork 1–2 Oct 2026) quedan enlazados a la elección sembrada; el `CIS` (sin `fieldwork_end`) queda nulo.
- Los tests del ciclo deben pasar sin tocar `ingestor/src/`; si alguno falla, es un hallazgo de las features 6/9 que se documenta en `progress/` y se para (no se parchea dentro de esta feature).

## Decisiones

- **El job es el encadenado de los dos comandos; no hay comando nuevo** (`sync-polls`) ni orquestador en Python: el plan fija el ciclo como `fetch-polls` + `ingest-polls` y la feature 9 lo dejó como interfaz explícita. Un comando nuevo duplicaría orquestación, añadiría superficie de CLI y obligaría a tocar `ingesta.md`.
- **`&&` en la cadena**: si el fetch falla, no se ingiere; el fallo es la señal (exit ≠ 0 + log) y el pase de resolución espera a la siguiente ejecución (12 h).
- **Cron como mecanismo canónico** (con launchd documentado como alternativa): la entrada es una línea auditable y el acceptance pide documentarla, no instalarla; un plist versionado sería configuración atada a una máquina.
- **Workflow placeholder en verde**: la topología de entornos se decidirá con la entrega; un job programado fallando en rojo cada 12 h en `main` sería ruido, y cablear ahora un secreto `DATABASE_URL` sería inventar configuración.
- **Log en `data/polls-sync.log`**: `data/` ya existe (cron no crea directorios para `>>`) y `*.log` está gitignored.
- **Tests con `cli.main()` y dobles** (fake opener + fixture `db`): mismo patrón que las features 6 y 9; ejercitan el ciclo real (parseo de argumentos, exit codes, registro en bronce, resolución) sin red y sin tocar los esquemas de la aplicación.
- **Tests de artefactos por subcadenas** (docs y workflow): es el patrón del repo (features 6 y 9); fijan el contrato sin acoplarse al texto completo.

## Alternativas descartadas

1. **Comando `sync-polls` que orqueste fetch + ingest**: más código, más CLI y una salida más que documentar para lo que un `&&` resuelve; el plan y la feature 9 fijan el ciclo como dos comandos.
2. **Script `scripts/polls-sync.sh` llamado por cron**: un fichero más para encapsular una línea; el `&&` documentado es autosuficiente y no añade rutas al repo.
3. **Workflow con el job real y `DATABASE_URL` por secreto**: la topología de entornos no existe todavía (la fija la entrega); el workflow fallaría cada 12 h en `main`.
4. **`schedule:` comentado hasta que exista entorno**: el acceptance pide el disparador en el fichero; el placeholder verde lo cumple sin ruido.
5. **Cron con `;` en vez de `&&`**: `ingest-polls` correría tras un fetch fallido y el exit code dejaría de reflejar el fallo del fetch (habría que capturarlo a mano).
6. **Test del ciclo con `subprocess` sobre el binario**: no añade cobertura frente a `cli.main()` con los dobles ya usados en 6 y 9, y complica el aislamiento de la base (habría que exportar `DATABASE_URL` de test y crear esquemas).
7. **launchd como mecanismo principal con plist versionado**: fichero de configuración atado a una máquina; el cron es una línea y el acceptance pide documentar la entrada.
8. **Cron horario o cada minuto**: el plan fija 2×/día; subir la frecuencia es cambiar la línea documentada.

## Interfaz para la feature 11

- Feature 11 (`polls_run`) ejecuta el mismo encadenado a mano (`uv run ingestor fetch-polls && uv run ingestor ingest-polls`) sobre la página real; la entrada de cron documentada aquí es la que quedará instalada para la operación 2×/día.
