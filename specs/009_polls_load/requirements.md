# Requisitos — `polls_load`

Feature `id 9` de [`feature_list.json`](../../feature_list.json). Alcance: loader y comando `ingest-polls` — registro del snapshot en bronce, parseo con el adaptador de la feature 8 y carga de `pollster`/`poll`/`poll_result` en `silver`, con guard de revisión y pase de resolución de elección. La descarga es de la feature 6; el lexer (7) y el adaptador (8) ya están specificados e implementados antes en la cadena.

Sin cambios de modelo: `pollster`, `poll` y `poll_result` existen desde la feature 5 (ERD ↔ `models.py` ↔ migración no aplican). Sin dependencias nuevas; se reutilizan `IngestError`, `sha256`/`slugify` (`elections/loaders/election.py`), `SOURCE` (`polls/fetch.py`) y `ELECTION_TYPE`/`PARTY_COLUMNS`/`parse_polls` (`polls/adapters/wikipedia_polls.py`).

## R1

CUANDO `ingest-polls` procesa un snapshot pendiente, el sistema DEBE registrarlo en `bronze.ingestion` con su sha256, su tamaño en bytes, `source = wikipedia-en` y `file_path` relativo a `RAW_DIR`.

## R2

CUANDO carga un snapshot, el sistema DEBE escribir todas las filas de plata de ese snapshot —get-or-create de `pollster` y `party`, borrado de `poll`/`poll_result` e inserción— en una única transacción.

## R3

El sistema DEBE buscar o crear cada `pollster` por el slug derivado del nombre de firma (`slugify`), reutilizando la fila existente sin duplicarla y creándola con ese nombre cuando falte.

## R4

El sistema DEBE buscar o crear cada `party` de los resultados por su slug, usando el nombre legible del adaptador (`PARTY_COLUMNS`) al crear el que falte (p. ej. `salf` → «Se Acabó La Fiesta», `alianca-cat` → «Aliança Catalana»).

## R5

El sistema DEBE insertar una fila de `poll` por cada fila del snapshot con `pollster_id`, `source` literal, `election_type` del adaptador (`congress`), `election_id` nulo, fechas de trabajo de campo, muestra, participación y `revision_id` leído del nombre del fichero.

## R6

El sistema DEBE insertar una fila de `poll_result` por cada resultado de la fila del snapshot, con `poll_id`, `party_id`, `pct`, `seats_min` y `seats_max`.

## R7

CUANDO carga un snapshot, el sistema DEBE reemplazar por completo el contenido de `poll` y `poll_result` (borrar todo antes de insertar) y NO DEBE tocar `pollster` ni `party`.

## R8

CUANDO la carga de un snapshot termina con el commit, el sistema DEBE marcar el fichero `processed` en `bronze.ingestion`.

## R9

CUANDO un snapshot ya está `processed` en bronce (mismo sha256), el sistema DEBE saltarlo sin volver a cargarlo.

## R10

SI el `revision_id` de un snapshot es anterior al máximo `poll.revision_id` ya cargado ENTONCES el sistema DEBE ignorarlo con un warning, sin cargarlo y sin añadirlo a `bronze.ingestion`.

## R11

CUANDO se pasa `--force`, el sistema DEBE procesar los snapshots aunque ya estén `processed` o sean anteriores al ya cargado.

## R12

El sistema DEBE enlazar cada sondeo con `election_id` nulo a la primera elección del mismo `election_type`, de ámbito nacional (sin CCAA ni municipio) y fecha estrictamente posterior a su `fieldwork_end`.

## R13

SI no existe ninguna elección posterior al trabajo de campo de un sondeo ENTONCES su `election_id` DEBE quedar nulo, sin error.

## R14

SI un sondeo no tiene `fieldwork_end` ENTONCES su `election_id` DEBE quedar nulo (no se enlaza).

## R15

El sistema DEBE ejecutar el pase de resolución al inicio de cada ejecución de `ingest-polls`, antes de decidir qué snapshots están pendientes, también cuando no haya ningún snapshot pendiente ni nuevo.

## R16

El pase de resolución DEBE considerar solo los sondeos con `election_id` nulo, de modo que repetirlo no modifique los ya enlazados.

## R17

SI una fila del snapshot no produce firma (literal de firma vacío o nombre de encuestadora vacío) ENTONCES el sistema DEBE abortar la carga con `IngestError`.

## R18

SI una fila del snapshot produce menos de dos partidos con valor ENTONCES el sistema DEBE abortar la carga con `IngestError`.

## R19

SI un porcentaje queda fuera de 0–100, un escaño fuera de 0–350 o `seats_min` es mayor que `seats_max` ENTONCES el sistema DEBE abortar la carga con `IngestError`.

## R20

SI la suma de porcentajes de un sondeo supera 100.5 ENTONCES el sistema DEBE registrar un warning y continuar la carga (la página no publica «otros»).

## R21

SI el snapshot no produce ningún sondeo ENTONCES el sistema DEBE abortar la carga con `IngestError` (protege `silver` de un borrado por deriva del formato).

## R22

SI la carga de un snapshot falla ENTONCES el sistema DEBE deshacer la transacción —sin dejar filas parciales en `silver`— y marcar el fichero `failed` en `bronze.ingestion`.

## R23

El comando `ingest-polls` DEBE aceptar una ruta opcional —un fichero `.wikitext` o un directorio— y procesar los snapshots que contenga.

## R24

El sistema DEBE procesar, cuando no se pasa ruta, los snapshots `.wikitext` bajo `RAW_DIR/polls/` (recursivo).

## R25

El comando DEBE salir con código 0 cuando todo queda `processed` o saltado —también sin snapshots pendientes— y con código 1 cuando alguna carga falla.

## R26

SI la ruta indicada no existe ENTONCES el sistema DEBE propagar `IngestError`.

## R27

SI un snapshot no está bajo `RAW_DIR` ENTONCES el sistema DEBE propagar `IngestError` (el bronce guarda rutas relativas a `RAW_DIR`).

## R28

SI el nombre de un snapshot no es `{entero}.wikitext` ENTONCES el sistema DEBE propagar `IngestError`.

## R29

El sistema DEBE actualizar `docs/ingestor/ingesta.md` con el comando `ingest-polls`, su comportamiento (bronce, guard, reemplazo, resolución de elección, validaciones) y las tablas de sondeos de `silver`.

## R30

El sistema DEBE actualizar `ingestor/AGENTS.md` (comando en «Comandos» y bullet de `src/ingestor/loaders/`) para documentar `polls.py`.

## R31

CUANDO la clave de un resultado no es un slug del mapeo (rótulo crudo de una columna desconocida, R8 del adaptador) el sistema DEBE registrar un warning y dar de alta el `party` con `slugify` de la clave como slug y la clave como nombre (p. ej. `FA` → `fa`/«FA»), reutilizándolo si ya existe.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «`uv run ingestor ingest-polls [ruta]` registra el fichero en `bronze.ingestion` (source wikipedia-en, sha256) y carga `pollster`/`poll`/`poll_result` en una transacción» | R1, R2, R3, R4, R5, R6, R7, R8 |
| «guard de revisión: un snapshot anterior al ya cargado se ignora con warning; `--force` lo reprocesa» | R9, R10, R11 |
| «resolución de elección: cada sondeo con `election_id` nulo se enlaza a la primera elección nacional al Congreso posterior a su trabajo de campo (mismo `election_type`); sin ella queda nulo, y el pase corre en cada ejecución aunque no haya snapshot nuevo» | R12, R13, R14, R15, R16 |
| «validaciones mínimas: cada fila con firma y ≥2 partidos, rangos de pct/seats, suma de porcentajes ≤ 100.5 como warning» | R17, R18, R19, R20 |
| «fallo → rollback y estado failed en `bronze.ingestion`» | R22 (y R2, R17–R19, R21) |
| «`docs/ingestor/ingesta.md` actualizado con los comandos nuevos» | R29, R30 |
| Extra: interfaz de entrada del comando (ruta, defecto y exit codes) | R23, R24, R25 |
| Extra: robustez del contrato de snapshots (ruta, ubicación y nombre) | R26, R27, R28 |
| Extra: guarda contra el snapshot vacío (protección del borrado total) | R21 |
| Extra: altas de partidos desde rótulos crudos de columnas desconocidas (resolución provisional; la cura el catálogo de party-norm, feature 14) | R31 |

## Notas de alcance

- **Reemplazo total**: `silver` refleja el último snapshot ingerido ; el histórico de revisiones vive en bronce. Por eso el borrado es de toda la tabla (`poll_result` y `poll`), no solo de las filas del snapshot.
- **Pase de resolución al inicio**: corre antes de seleccionar snapshots pendientes («corre en cada ejecución, también sin snapshot nuevo»); los sondeos de un snapshot cargado en esa misma ejecución quedan enlazados en la siguiente ejecución (≤12 h con el job programado de la feature 10). La alternativa de resolver también tras la carga se descarta en [`design.md`](design.md).
- **«Ámbito nacional»**: columnas de ámbito (`autonomous_community_ine_code`, `municipality_id`) nulas en `silver.election`; hoy todos los sondeos son al Congreso nacional (`ELECTION_TYPE` del adaptador).
- **R21 es una validación extra** a la lista mínima del acceptance: un parseo vacío (deriva del formato) haría un borrado total sin inserción; se aborta la carga.
- **Sin cambios de modelo**: esta feature no toca `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica).

## Nota de verificación

- R1–R28: tests en `ingestor/tests/test_polls_load.py`, con la fixture de BD de `ingestor/tests/conftest.py` (esquemas Postgres aislados `polls_test_bronze`/`polls_test_silver` vía `schema_translate_map`; si Postgres no responde, los tests se saltan —la CI lo levanta como servicio—). Snapshots de entrada: fixtures `ingestor/tests/fixtures/wikipedia_polls/load_small.wikitext` y `load_other.wikitext` copiadas a `tmp_path` con el `{revid}.wikitext` deseado, y cadenas sintéticas inline para las validaciones. Sin red ni `refs/`.
- R29: test que lee `docs/ingestor/ingesta.md` y comprueba subcadenas estables (`ingest-polls`, `wikipedia-en`, `revision_id`, `failed`).
- R30: test que lee `ingestor/AGENTS.md` y comprueba subcadenas estables (`ingest-polls`, `polls.py`).
