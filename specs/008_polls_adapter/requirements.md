# Requisitos — `polls_adapter`

Feature `id 8` de [`feature_list.json`](../../feature_list.json); tarea 4 del plan [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), §§ «La fuente» y «Parser (wikitexto)». Alcance: `polls/adapters/wikipedia_polls.py` — reglas de la fuente de sondeos de Wikipedia (secciones y tablas por año, cabecera a dos filas, filas → sondeos, fechas, números, mapeo de partidos, saltos) — sobre el lexer genérico de la feature 7 (`polls/parsers/wikitext.py`). No descarga (feature 6) ni carga en `silver` (feature 9).

Formas verificadas en el snapshot real (2026-10-17) que fijan los requisitos: tablas por año bajo `====Voting intention estimates====` (`2026 (after FA)` — vacía en esa revisión —, `2026 (before FA)`, `2025`, `2024`, `2023`); cabecera a dos filas `!` (la segunda, de `{{party color|…}}`, se ignora); 17–20 columnas; filas separadoras `| colspan="17" style="background:#A0A0A0"|`; filas de resultado `|- style="background:#EFEFEF;"`; celdas de partido con `%` + `<br/>` + `{{font|…|text=escaños}}`, `–`, `?`, `<2.0` y rangos `135/137`; fechas `10–11 Oct`, `5 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`, `?`; muestras `1,000`/`?`; participación `67.6`/`66`/`?`.

## R1

CUANDO `parse_polls` recibe el wikitexto de la página de sondeos, el sistema DEBE devolver una lista de `PollRow` en el orden de la página —una por fila de datos de las tablas por año— con `source`, `pollster_name`, `fieldwork_start`, `fieldwork_end`, `sample_size`, `turnout` y `results` (diccionario slug de partido → `PollResultRow` con `pct`, `seats_min` y `seats_max`, en orden de columna).

## R2

El sistema DEBE tomar los sondeos únicamente de las tablas de las subsecciones por año (`=====<año>…=====`) de la sección `====Voting intention estimates====` —todas las subsecciones, aunque haya varias de un mismo año, y todas las tablas de cada subsección— y NO DEBE ingerir tablas de otras secciones de la página.

## R3

CUANDO una tabla tiene una fila de cabecera con los rótulos seguida de otra fila de cabecera (la de `{{party color|…}}`), el sistema DEBE identificar las columnas con la primera fila y NO DEBE procesar la segunda como fila de datos.

## R4

El sistema DEBE localizar las cuatro columnas fijas (`Polling firm/Commissioner`, `Fieldwork date`, `Sample size`, `Turnout`) por su rótulo de cabecera, no por su posición.

## R5

El sistema DEBE descubrir las columnas de partido por el rótulo de su celda de cabecera —el texto del wikilink (último parámetro, o el valor de `link=` cuando no hay rótulo) o el propio texto si no hay wikilink— y NO DEBE asignarlas por su posición.

## R6

El sistema DEBE mapear los rótulos de partido conocidos a los slugs de `silver.party`: `PP`→`pp`, `PSOE`→`psoe`, `Vox`→`vox`, `Sumar`→`sumar`, `ERC`→`erc`, `Junts`→`jxcat-junts`, `EH Bildu`→`eh-bildu`, `PNV`→`eaj-pnv`, `BNG`→`bng`, `CCa`→`cca`, `UPN`→`u-p-n`, `Adelante Andalucía (2021)`→`adelante-andalucia`, `Podemos`→`podemos`, `SALF`→`salf`, `Aliança.cat`→`alianca-cat`.

## R7

El sistema DEBE exponer para `SALF` y `Aliança.cat` el slug y el nombre con el que la carga las creará: `salf`/«Se Acabó La Fiesta» y `alianca-cat`/«Aliança Catalana».

## R8

SI el rótulo de una columna de partido no está en el mapeo ENTONCES el sistema DEBE registrar un warning con el rótulo y DEBE ignorar esa columna (sus celdas no producen resultados).

## R9

El sistema DEBE ignorar la columna `Lead` sin warning y sin resultado.

## R10

CUANDO una fila tiene una única celda con atributo `colspan` (fila separadora), el sistema DEBE saltarla sin warning.

## R11

CUANDO los atributos de una fila contienen `background:#EFEFEF` (fila del resultado de una elección), el sistema DEBE saltarla sin warning.

## R12

CUANDO la celda de una columna de partido tiene texto, el sistema DEBE interpretar su primera línea como porcentaje: un número DEBE guardarse como `pct`; `?`, `<2.0`, `–` o vacío DEBEN guardarse como `pct` nulo.

## R13

CUANDO la celda de una columna de partido tiene una segunda línea, el sistema DEBE interpretarla como proyección de escaños: `N` DEBE guardarse como `seats_min = seats_max = N`, `N/M` como `seats_min = N` y `seats_max = M`, y `?` o vacío como nulos.

## R14

El sistema DEBE emitir un resultado por columna solo cuando su porcentaje o sus escaños tienen valor, y NO DEBE emitir resultados para celdas `–` ni para celdas sin valores.

## R15

CUANDO la celda de fecha contiene un día único (`5 Oct`), el sistema DEBE guardarlo como `fieldwork_start` y `fieldwork_end` (la fuente publica la fecha de publicación cuando desconoce el trabajo de campo).

## R16

CUANDO la celda de fecha contiene un rango (`10–11 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`), el sistema DEBE resolver `fieldwork_start` y `fieldwork_end` con el año de la subsección, restando uno al año de inicio cuando el mes inicial es posterior al final (cruce de año).

## R17

CUANDO la celda de fecha es `?`, el sistema DEBE dejar `fieldwork_start` y `fieldwork_end` nulos.

## R18

CUANDO la celda de muestra contiene un entero con separador de millares (`1,000`), el sistema DEBE guardarlo como entero; `?` DEBE guardarse como nulo.

## R19

CUANDO la celda de participación contiene un número (`67.6`, `66`), el sistema DEBE guardarlo como `Decimal`; `?` DEBE guardarse como nulo.

## R20

El sistema DEBE emitir una fila propia por cada fila de datos —reestimaciones del CIS incluidas— y DEBE guardar en `source` el literal de su celda de firma (p. ej. `SocioMétrica/El Español`, `CIS (Target Point)`).

## R21

El sistema DEBE extraer `pollster_name` del literal de la firma: el texto anterior a la primera `(` o `/` (`SocioMétrica/El Español` → `SocioMétrica`; `CIS (Target Point)` → `CIS`).

## R22

SI una celda de fecha, muestra, participación, porcentaje o escaños no encaja en las formas conocidas ENTONCES el sistema DEBE registrar un warning y guardar el valor como nulo.

## R23

SI una fila de datos tiene un número de celdas distinto del de la cabecera ENTONCES el sistema DEBE registrar un warning y saltarla.

## R24

SI la primera fila de una tabla no contiene los cuatro rótulos fijos ENTONCES el sistema DEBE registrar un warning y saltar la tabla.

## R25

SI la sección `Voting intention estimates` no aparece ENTONCES el sistema DEBE registrar un warning y devolver una lista vacía.

## R26

El sistema DEBE declarar `ELECTION_TYPE = "congress"` en el módulo del adaptador.

## R27

El sistema DEBE implementar el adaptador en `polls/adapters/wikipedia_polls.py` usando únicamente la biblioteca estándar y `polls/parsers/wikitext.py`, sin red, sin disco y sin base de datos.

## R28

El sistema DEBE cubrir las reglas con fixtures en `ingestor/tests/fixtures/wikipedia_polls/` (recortes literales del snapshot real + casos sintéticos) y los tests NO DEBEN depender de la red, de `data/raw/` ni de `refs/`.

## R29

El sistema DEBE actualizar `ingestor/AGENTS.md` (bullet de `adapters/`) para documentar `wikipedia_polls.py`.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «`polls/adapters/wikipedia_polls.py` produce sondeos con firma, fechas (rangos, cruce de año, fecha de publicación como aproximación), muestra, participación y resultados por partido» | R1, R2, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R26 |
| «columnas de partido descubiertas por cabecera (nunca por posición); columna desconocida → warning y se ignora; la columna Lead se ignora» | R3, R4, R5, R8, R9 |
| «mapeo a slugs de `silver.party`; SALF y Aliança.cat se crean; reestimaciones del CIS (Target Point, Ateneo del Dato…) se cargan como filas con source literal» | R6, R7, R20, R21 |
| «filas separadoras y la fila del resultado de 2023 se saltan» | R10, R11 |
| «fixtures recortadas reales + sintéticas en `tests/fixtures/wikipedia_polls/`» | R28 |
| Extra: robustez ante deriva del formato (plan §Flecos: «warning y a seguir») | R22, R23, R24, R25 |
| Extra: contrato para la feature 9 (`ELECTION_TYPE`) y pureza del adaptador | R26, R27 |
| Extra: regla de documentación (módulo nuevo de `adapters/` documentado en el mismo commit) | R29 |

## Notas de alcance

- **`FA` (Frente Amplio)**: el snapshot verificado trae esa columna en la tabla `2026 (after FA)`, que no está en el mapeo del plan. Cae en R8: warning y se ignora. Añadirla es curación de identidades de partido (plan §Flecos), fuera de esta feature.
- **Creación de partidos**: el adaptador no toca la base de datos; expone slug y nombre (R7) para que la carga (feature 9, `get-or-create`) cree `salf` y `alianca-cat`.
- **Sin cambios de modelo**: esta feature no toca `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica).

## Nota de verificación

- R1–R24: tests en `ingestor/tests/test_wikipedia_polls.py` sobre fixtures en `ingestor/tests/fixtures/wikipedia_polls/` (recortes reales `real_2026_head.wikitext` y `real_2023_tail.wikitext`; sintéticas `synthetic_dates.wikitext`, `synthetic_cells.wikitext`, `synthetic_columns.wikitext` y `synthetic_out_of_scope.wikitext`) y cadenas inline para los casos de robustez (R22–R25). Sin red ni `refs/`.
- R26: test del valor de `ELECTION_TYPE`.
- R27: test que lee el fuente del módulo y comprueba que no importa nada fuera de la stdlib ni de `ingestor.polls.parsers.wikitext`, y que no contiene `urlopen`, `socket`, `requests`, `httpx`, `open(`, `sqlalchemy` ni `SessionLocal`.
- R28: test que comprueba que las seis fixtures existen y que todos los tests parsean sin red.
- R29: test que lee `ingestor/AGENTS.md` y comprueba las subcadenas `wikipedia_polls.py` y `sondeos`.
