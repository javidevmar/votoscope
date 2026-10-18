# Requisitos — `polls_fetch`

Feature `id 6` de [`feature_list.json`](../../feature_list.json). Alcance: descarga del snapshot de wikitexto de **revisión fija** de la página de sondeos al bronce (`data/raw/polls/`). El parseo del wikitexto (features 7–8) y la carga en `silver` (feature 9) quedan fuera.

El alcance del snapshot es la **página completa** (todas las tablas de encuestas bajo *Voting intention estimates*, desde las generales del 23-jul-2023 hasta hoy): `fetch-polls` baja el wikitexto entero, sin recortar secciones.

## R1

CUANDO se ejecuta `uv run ingestor fetch-polls` sin `--page`, el sistema DEBE resolver la revisión actual de la página por defecto («Opinion polling for the 2026 Spanish general election») con una petición HTTP a `https://en.wikipedia.org/w/api.php` cuyos parámetros incluyan `action=query`, `prop=revisions`, `rvprop=ids|timestamp`, `redirects=1`, `format=json` y `formatversion=2`, con `titles` fijado al título de la página por defecto.

## R2

CUANDO la respuesta de la API contiene una revisión, el sistema DEBE descargar el wikitexto de esa revisión con una petición HTTP a `index.php?oldid={revid}&action=raw` (la revisión queda fijada por `oldid`).

## R3

El sistema DEBE escribir el wikitexto descargado en `<RAW_DIR>/polls/wikipedia-en/2026-general/{revid}.wikitext`, creando los directorios intermedios que falten.

## R4

CUANDO la revisión resuelta ya está en disco como `{revid}.wikitext`, el sistema DEBE omitir la descarga y no escribir ningún fichero, realizando únicamente la petición de resolución a la API.

## R5

DONDE se pasa la opción `--page <título>`, el sistema DEBE resolver y descargar la revisión de esa página en lugar de la de por defecto.

## R6

El sistema DEBE derivar la carpeta del snapshot del título de la página: `2026-general` para la página por defecto y, para cualquier otra, el título en minúsculas con los tramos no alfanuméricos unidos por guiones (por ejemplo, «Opinion polling for the 2027 Spanish general election» → `opinion-polling-for-the-2027-spanish-general-election`).

## R7

El sistema DEBE realizar las peticiones HTTP con `urllib` de la biblioteca estándar y NO DEBE añadir dependencias nuevas al proyecto.

## R8

El sistema DEBE enviar en cada petición HTTP una cabecera `User-Agent` que identifique al proyecto (`votoscope`), no la de `urllib` por defecto.

## R9

El sistema DEBE aplicar un timeout de 30 segundos a cada petición HTTP.

## R10

SI una petición HTTP falla por error de red o de protocolo ENTONCES el sistema DEBE reintentarla una sola vez antes de darla por fallida.

## R11

SI la petición vuelve a fallar tras el reintento ENTONCES el sistema DEBE propagar `IngestError` sin escribir ningún fichero del snapshot.

## R12

SI `fetch-polls` no consigue resolver o descargar la revisión ENTONCES el sistema DEBE registrar el error por log y salir con un exit code distinto de 0.

## R13

SI la respuesta de la API no contiene ninguna revisión para la página (página ausente o renombrada sin redirección) ENTONCES el sistema DEBE propagar `IngestError` sin intentar la descarga.

## R14

CUANDO `fetch-polls` termina con éxito (descargando el snapshot o por «sin novedades»), el sistema DEBE salir con exit code 0.

## R15

El sistema DEBE registrar por log, a nivel INFO, la revisión resuelta (revid y timestamp) y si el snapshot se descargó o ya estaba en disco.

## R16

El sistema DEBE aceptar un transporte HTTP inyectado, de modo que la resolución, la descarga y el camino «sin novedades» se puedan ejercitar en tests sin red con fixtures JSON de la respuesta de la API.

## R17

El sistema DEBE actualizar `.agents/architecture.md` con el matiz de que los sondeos de Wikipedia se descargan por CLI (`fetch-polls`), como excepción acotada a la regla «el ingestador no descarga nada», y con la ruta del bronce de sondeos (`data/raw/polls/`).

## R18

El sistema DEBE actualizar `ingestor/AGENTS.md` con el comando `fetch-polls`, el módulo `src/ingestor/polls/fetch.py` y el matiz de que los sondeos se descargan por CLI.

## R19

El sistema DEBE actualizar `docs/ingestor/ingesta.md` con una sección de `fetch-polls` (comportamiento, ruta del snapshot, timeout y reintento, exit codes), como exige la regla de documentación de `ingestor/AGENTS.md` para todo cambio de CLI.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «descarga `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext` vía API (revisión fija, `redirects=1`)» | R1, R2, R3, R6 |
| «si esa revisión ya está en disco no la repite: el ciclo sin novedades es una sola llamada a la API y exit 0» | R4, R14 |
| «`--page` permite apuntar a otra página; `urllib` de la stdlib, User-Agent identificativo, timeout y un reintento» | R5, R6, R7, R8, R9, R10 |
| «tests sin red: parseo de la respuesta de la API con fixture JSON y camino "sin novedades"» | R16 (los tests de R1–R15 corren con el transporte inyectado) |
| «matiz "los sondeos se descargan por CLI" reflejado en `.agents/architecture.md` e `ingestor/AGENTS.md`» | R17, R18 |
| Extra: regla de documentación de `ingestor/AGENTS.md` (todo cambio de CLI actualiza `ingesta.md` en el mismo commit) | R19 |

## Nota de verificación

- R1–R16: tests en `ingestor/tests/test_polls_fetch.py` con transporte HTTP inyectado (fake opener) y fixtures JSON reales en `ingestor/tests/fixtures/wikipedia_polls/`; ningún test usa red.
- R10–R12: la caída de red se simula con un fake opener que lanza `URLError` (clase estándar de `urllib.error`).
- R13: fixture `api_missing.json` (respuesta real de página ausente).
- R15: `caplog` a nivel INFO.
- R17–R19: tests que leen los ficheros de documentación desde `ingestor/tests/test_polls_fetch.py` y comprueban los fragmentos acordados en `design.md`.
