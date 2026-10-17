# Diseño — `polls_fetch`

Feature 6. Plan de iniciativa: [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), §§ «La fuente» y «Obtención (bronce)»; materializa la decisión 1 del plan («los sondeos se descargan por CLI»). Solo descarga al bronce: sin parseo (7–8) y sin base de datos (9).

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica). Sin dependencias nuevas (`urllib` es stdlib). Sin excepciones nuevas: se reutiliza `IngestError` (`ingestor/errors.py`). En caso de necesitar modificación de modelo, siempre pregunta al usuario y anota el cambio.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/fetch.py` — resolución de la revisión actual + descarga del wikitexto |
| modificar | `ingestor/src/ingestor/cli.py` — subcomando `fetch-polls` con `--page` |
| crear | `ingestor/tests/test_polls_fetch.py` — tests sin red (R1–R19) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/api_revision.json` — respuesta real de la API con revisión |
| crear | `ingestor/tests/fixtures/wikipedia_polls/api_missing.json` — respuesta real de página ausente |
| modificar | `.agents/architecture.md` — matiz de la descarga por CLI (R17) |
| modificar | `ingestor/AGENTS.md` — comando, módulo y matiz (R18) |
| modificar | `docs/ingestor/ingesta.md` — sección de `fetch-polls` (R19) |

## Firmas nuevas — `src/ingestor/polls/fetch.py`

```python
Opener = Callable[..., IO[bytes]]  # compatible con urllib.request.urlopen

DEFAULT_PAGE = "Opinion polling for the 2026 Spanish general election"
DEFAULT_SNAPSHOT_DIR = "2026-general"
SOURCE = "wikipedia-en"
API_URL = "https://en.wikipedia.org/w/api.php"
RAW_URL = "https://en.wikipedia.org/w/index.php"
USER_AGENT = "votoscope-ingestor/0.1 (https://github.com/javidevmar/votoscope)"
TIMEOUT_SECONDS = 30
ATTEMPTS = 2  # el intento inicial + un reintento


class FetchOutcome(NamedTuple):
    revid: int
    timestamp: str
    path: Path
    downloaded: bool


def parse_revision_response(payload: bytes) -> tuple[int, str]: ...
def snapshot_dir(page: str) -> str: ...
def snapshot_path(page: str, revid: int, raw_dir: Path) -> Path: ...
def fetch_snapshot(
    page: str = DEFAULT_PAGE, *, raw_dir: Path, opener: Opener | None = None
) -> FetchOutcome: ...
```

Internos: `_request(url, opener) -> bytes` (User-Agent, timeout, reintento), `_api_url(page) -> str` y `_raw_url(revid) -> str`.

Detalles de implementación que fijan el contrato:

- `opener=None` **se resuelve en tiempo de llamada** (`opener = opener or urlopen`), no como valor por defecto del parámetro, para que los tests del CLI puedan parchear `ingestor.polls.fetch.urlopen` con `monkeypatch`.
- `_request` usa `Request(url, headers={"User-Agent": USER_AGENT})` y `opener(request, timeout=TIMEOUT_SECONDS)`, y lee la respuesta con `with ... as response: response.read()` (un fake basado en `io.BytesIO` cumple el protocolo de contexto).
- `fetch_snapshot` no importa `settings` ni `db`: recibe `raw_dir` por parámetro y no abre sesión de base de datos (el comando funciona sin Postgres; el registro en `bronze.ingestion` lo hará `ingest-polls`, feature 9).

## Flujo de `fetch_snapshot`

1. `resolve_revision(page)`: una petición a `_api_url(page)`; `parse_revision_response` devuelve `(revid, timestamp)`; log INFO de la revisión resuelta (**única** llamada a la API en el camino sin novedades).
2. `path = snapshot_path(page, revid, raw_dir)`.
3. Si `path` existe → log INFO «up to date» y `FetchOutcome(..., downloaded=False)` sin más peticiones ni escritura.
4. Si no existe → petición a `_raw_url(revid)`, `path.parent.mkdir(parents=True, exist_ok=True)` y `path.write_bytes(data)` (los ~650 KB caben en memoria; no hay fichero parcial si la petición falla); log INFO «downloaded» y `FetchOutcome(..., downloaded=True)`.

Errores: fallo de red persistente → `IngestError("request failed after 2 attempts: <url>")` (R11); respuesta sin revisión → `IngestError("API response without a revision (missing page?)")` (R13). Los errores de red se reintentan una vez con log WARNING entre intentos (`except OSError`, que cubre `URLError`, `HTTPError` y `TimeoutError`).

## URLs

- Resolución (R1): `API_URL` + `urlencode({"action": "query", "prop": "revisions", "rvprop": "ids|timestamp", "redirects": "1", "format": "json", "formatversion": "2", "titles": page})`. `formatversion=2` devuelve `pages` como lista y `revisions` como lista (respuestas reales capturadas el 2026-10-17).
- Descarga (R2): `RAW_URL` + `urlencode({"oldid": revid, "action": "raw"})`.
- Los tests comparan los parámetros decodificados (`urllib.parse.parse_qs`), no la cadena cruda.

Formas reales de la respuesta (base de las fixtures):

```json
{"batchcomplete":true,"query":{"pages":[{"pageid":72114276,"ns":0,
 "title":"Opinion polling for the 2026 Spanish general election",
 "revisions":[{"revid":1380713440,"parentid":1380368158,"timestamp":"2026-10-17T11:34:38Z"}]}]}}
```

```json
{"batchcomplete":true,"query":{"pages":[{"ns":0,
 "title":"Opinion polling for the 9999 Spanish general election","missing":true}]}}
```

`parse_revision_response`: `json.loads` → `query.pages[0]`; si falta `pages`, la página trae `missing` o no hay `revisions` → `IngestError`; si no, `revisions[0]` → `(revid, timestamp)`. Los campos extra (`redirects`, `normalized`, `parentid`…) se ignoran.

## Ruta del snapshot (R3, R6)

`snapshot_path` = `raw_dir / "polls" / SOURCE / snapshot_dir(page) / f"{revid}.wikitext"`.

`snapshot_dir`: si el título (normalizando `_`→espacio) es `DEFAULT_PAGE` → `DEFAULT_SNAPSHOT_DIR` (`2026-general`, que fija el acceptance); para el resto, slug `re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")`. La alternativa (slugificar también la página por defecto) se descarta en «Alternativas» porque rompería la ruta fijada. El `--page` queda listo para el renombrado futuro («2027…»); el contraste con la página española seguiría siendo manual (mismo host, plan §La fuente).

## CLI — `src/ingestor/cli.py`

- Nuevo subparser:

```python
fetch = subparsers.add_parser(
    "fetch-polls",
    help="download the fixed-revision wikitext snapshot of the polls page",
)
fetch.add_argument("--page", default=DEFAULT_PAGE, help="Wikipedia page title (default: 2026 general election)")
```

- Handler dentro del `try` existente:

```python
if args.command == "fetch-polls":
    fetch_snapshot(args.page, raw_dir=settings.raw_dir)
    return 0
```

Exit codes: 0 en descarga y en «sin novedades» (R14); 1 vía el `except IngestError` ya existente, que además registra `logger.error("%s", error)` (R12). El comando no toca la base de datos.

## Logs (R15)

Fijados para que el test los compruebe por subcadena:

- `logger.info("resolved page=%s revid=%s timestamp=%s", page, revid, timestamp)`
- `logger.info("downloaded snapshot %s", path)`
- `logger.info("snapshot up to date: %s", path)`
- `logger.warning("request failed (%s); retrying once", url)` (reintento)

En el test se parchea `ingestor.settings.settings.raw_dir` al `tmp_path` (pydantic permite asignar atributos) y `ingestor.polls.fetch.urlopen`.

## Tests — `ingestor/tests/test_polls_fetch.py`

Fake opener local al fichero: registra `(request, timeout)` y devuelve `io.BytesIO(payload)`; variantes que lanzan `URLError` las N primeras llamadas. `REPO_ROOT = Path(__file__).resolve().parents[2]` (patrón de `test_polls_model.py`).

| Test previsto | Cubre |
| --- | --- |
| `test_parse_revision_response` (fixture `api_revision.json`) | R1 |
| `test_parse_missing_page_raises` (fixture `api_missing.json`) | R13 |
| `test_fetch_queries_current_revision` (params de la 1.ª petición) | R1, R5 |
| `test_fetch_downloads_fixed_revision` (URL `oldid`/`action=raw`; fichero escrito con los bytes) | R2, R3 |
| `test_fetch_creates_missing_directories` (`tmp_path` anidado) | R3 |
| `test_fetch_skips_existing_revision` (fichero previo: 1 sola llamada, contenido intacto, `downloaded is False`) | R4 |
| `test_user_agent_header` (`request.get_header("User-agent")` contiene `votoscope`) | R8 |
| `test_timeout_applied` (kwarg `timeout == TIMEOUT_SECONDS`) | R9 |
| `test_retry_once_then_success` (2 llamadas, warning) / `test_retry_gives_up` (`IngestError`, sin fichero) | R10, R11 |
| `test_page_option_title_and_dir` (`--page` cambia `titles`; slug de carpeta) / `test_default_dir` (`2026-general`) | R5, R6 |
| `test_cli_fetch_polls_downloads` / `test_cli_fetch_polls_no_news` (`main([...]) == 0`) | R14, R16 |
| `test_cli_failure_exit_1` (red caída → `main(...) == 1` y log ERROR) | R12 |
| `test_logs_revision_and_outcome` (`caplog` INFO: `revid=` + `downloaded snapshot`/`up to date`) | R15 |
| `test_no_real_urlopen_used` (`ingestor.polls.fetch.urlopen` parcheado a fallar + opener inyectado) | R16 |
| `test_stdlib_only` (`requests`/`httpx` fuera de `sys.modules`; `ingestor.polls.fetch.urlopen.__module__ == "urllib.request"`) | R7 |
| `test_docs_architecture`, `test_docs_ingestor_agents`, `test_docs_ingesta` | R17, R18, R19 |

La fixture `api_revision.json` es la respuesta real recortada de la tabla de arriba (capturada el 2026-10-17; revid `1380713440`); `api_missing.json`, la de página ausente. El wikitexto de prueba es un recorte pequeño real de la página (no los ~650 KB).

## Documentación (texto pretendido)

- `.agents/architecture.md` (R17): la frase «El ingestador no descarga nada: trabaja sobre los ficheros que haya en `data/raw/`.» pasa a distinguir datos electorales (siguen siendo manuales) de sondeos: «…Excepción acotada: los sondeos de Wikipedia se descargan por CLI (`uv run ingestor fetch-polls`), porque la revisión fija forma parte del contrato del snapshot.» Además, en «Flujo de datos» se añade la ruta del bronce de sondeos: `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext` (comprimida ya en la página «Bronze polls» del ERD, feature 5).
- `ingestor/AGENTS.md` (R18): en «Ficheros», bullet de `src/ingestor/polls/` (con `fetch.py`); en «Comandos», `uv run ingestor fetch-polls [--page <título>]`; y el matiz «los datos electorales se siguen descargando a mano; los sondeos se descargan por CLI porque la revisión fija es parte del contrato del snapshot».
- `docs/ingestor/ingesta.md` (R19): sección `### \`ingestor fetch-polls [--page <título>]\`` bajo «Comandos»: resolución de la revisión, descarga `oldid`/`action=raw`, ruta `RAW_DIR/polls/wikipedia-en/` (`2026-general/` por defecto), «sin novedades = una sola petición y exit 0», timeout/reintento y que no toca la base de datos (el registro en bronce es de `ingest-polls`). La feature 9 extenderá este documento con `ingest-polls`.

Los tests de docs comprueban subcadenas estables, no el texto completo: R17 → `fetch-polls` y `se descargan por CLI`; R18 → `fetch-polls`, `fetch.py` y `se descargan por CLI`; R19 → `fetch-polls` y `polls/wikipedia-en/`.

## Decisiones

- **`urllib` (stdlib)**: el acceptance y el plan lo fijan; evita la puerta de dependencias nuevas y basta para dos GET.
- **Sin registro en bronce desde `fetch-polls`**: el plan asigna el registro `bronze.ingestion` a `ingest-polls` (feature 9); así `fetch-polls` no necesita Postgres y el snapshot queda inmutable en disco antes de registrarse.
- **Escribir tras descargar completo, con `write_bytes`**: nada que limpiar si falla la red; no se escribe nunca sobre un `{revid}.wikitext` existente (bronce inmutable).
- **`formatversion=2`**: listas en vez de diccionarios con `pageid` como clave; parseo trivial.
- **`except OSError` para el reintento**: cubre `URLError`, `HTTPError` y `TimeoutError` sin enumerarlos; reintentar un 4xx es inocuo (una sola vez).
- **Un solo `IngestError`**: sin jerarquía nueva; el CLI ya traduce `IngestError` a exit 1 + `logger.error`.
- **Carpeta por título con caso especial `2026-general`**: reproduce la ruta del acceptance y prepara el renombrado de página; el caso especial vive junto a la constante `DEFAULT_PAGE`.

## Alternativas descartadas

1. **`curl` a mano** (ya descartada en el plan): cada refresco dependería de que alguien recuerde la revisión exacta; sin test posible sin red.
2. **`requests`/`httpx`**: dependencia nueva sin necesidad; prohibido añadir sin consentimiento explícito.
3. **Descargar con la API (`prop=revisions&rvprop=content&rvslots=main`)**: payload más grande y anidado; `index.php?oldid=…&action=raw` devuelve el wikitexto canónico tal cual (verificado: 651.802 bytes, HTTP 200).
4. **Descargar a un fichero temporal y `os.replace`**: resuelve un problema que no existe aquí (~650 KB en memoria; una sola escritura) y añade ficheros temporales que el cierre de sesión prohíbe.
5. **Registrar `bronze.ingestion` desde `fetch-polls`**: duplicaría el registro que el plan asigna a `ingest-polls` y haría que el fetch necesitase Postgres.
6. **Opciones extra `--dir`/`--host`**: YAGNI; el slug del título cubre el renombrado y el contraste con la página española es manual (plan §La fuente). Se añadirían el día que se scripte el contraste.
