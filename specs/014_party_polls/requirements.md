# Requisitos — `party_polls`

Feature `id 14` de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`). Depende de la feature 12 ([`specs/012_party_catalog/`](../012_party_catalog/)): el catálogo `ingestor/src/ingestor/data/party_catalog.toml` y el módulo `ingestor/src/ingestor/parties.py` (`normalize`, `slugify`, `Catalog`, `load_catalog`, `PartyResolver`); y de la feature 13 ([`specs/013_party_reload/`](../013_party_reload/)), que ya resolvió el loader de elecciones por el mismo catálogo.

Alcance: el adaptador de sondeos (`ingestor/src/ingestor/polls/adapters/wikipedia_polls.py`, hoy con la tabla ad-hoc `PARTY_COLUMNS`) resuelve sus rótulos de columna contra el catálogo compartido, y el loader de sondeos (`ingestor/src/ingestor/polls/loaders/polls.py`, hoy con `_PARTY_NAMES` y `_party_slug`) resuelve sus claves con `PartyResolver`; con el test de que la misma marca acaba en una única fila de `party` en `poll_result` y `party_election`, y la documentación viva del mapeo puesta al día (`docs/ingestor/ingesta.md` §«Comportamiento de `ingest-polls`»).

Contexto (absorbido): hoy los sondeos resuelven sus rótulos con una tabla propia del adaptador (`PARTY_COLUMNS`, quince rótulos → slug/nombre) y el loader crea o reutiliza `party` por el slug de esa tabla (`_PARTY_NAMES`); un rótulo desconocido se conserva con el rótulo crudo y un warning, y el loader lo da de alta con el warning `unknown party label`. Con el catálogo compartido de la 12 y la resolución `catálogo → nombre existente → alta con warning`, la misma marca debe acabar en la misma fila de `party` tanto si viene de una candidatura del `03` como de una columna de la wiki; es la condición para que `gold` y la web puedan unir sondeos y resultados por partido.

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican): `party` y `poll_result` valen tal cual. Sin dependencias nuevas. Sin excepciones nuevas (`IngestError`). Sin cambios de CLI.

## R1

El adaptador de sondeos DEBE resolver cada rótulo de columna de partido contra el catálogo compartido (`load_catalog()` y `Catalog.lookup`), en vez de contra una tabla de mapeo propia.

## R2

CUANDO un rótulo de columna tiene ficha en el catálogo, el adaptador DEBE usar el `slug` de la ficha como clave del resultado de esa columna.

## R3

SI un rótulo de columna no tiene ficha en el catálogo ENTONCES el adaptador DEBE conservar la columna con el rótulo crudo como clave del resultado.

## R4

CUANDO el adaptador conserva una columna sin ficha, el sistema DEBE registrar el warning `unknown party column: <rótulo>` (el sondeo se carga igual: la deriva de la fuente nunca es una excepción).

## R5

Las quince etiquetas que hoy cubre `PARTY_COLUMNS` DEBEN producir las mismas claves que esa tabla (`PP`→`pp`, `PSOE`→`psoe`, `Vox`→`vox`, `Sumar`→`sumar`, `ERC`→`erc`, `Junts`→`jxcat-junts`, `EH Bildu`→`eh-bildu`, `PNV`→`eaj-pnv`, `BNG`→`bng`, `CCa`→`cca`, `UPN`→`u-p-n`, `Adelante Andalucía (2021)`→`adelante-andalucia`, `Podemos`→`podemos`, `SALF`→`salf`, `Aliança.cat`→`alianca-cat`), incluida la auto-resolución de cada slug del catálogo a su propia ficha (`lookup(<slug>)` devuelve la ficha de ese slug).

## R6

El adaptador NO DEBE conservar la tabla `PARTY_COLUMNS` ni la clase `PartyColumn`.

## R7

`wikipedia_polls.py` NO DEBE importar nada fuera de la biblioteca estándar y `ingestor.*` (con `ingestor.parties` admitido), ni acceder a red ni a base de datos.

## R8

CUANDO se carga un snapshot, el loader DEBE resolver cada clave de resultado (slug del catálogo o rótulo crudo) con la resolución compartida `PartyResolver` (`parties.py`: catálogo → nombre existente → alta con warning).

## R9

El loader NO DEBE mantener tablas locales de mapeo o de nombres de partido (`_PARTY_NAMES`, `_party_slug`).

## R10

SI la clave de resultado no tiene ficha en el catálogo NI coincide por normalización con el `name` de una fila de `party` existente ENTONCES el loader DEBE crear la fila con `name` igual a la clave literal y registrar el warning `unknown party label: <clave> -> <slug>`.

## R11

CUANDO la misma marca aparece en la candidatura de una elección (`party_election`) y en el resultado de un sondeo (`poll_result`), el sistema DEBE referenciar una única fila de `silver.party`.

## R12

CUANDO se recarga un snapshot, el sistema NO DEBE duplicar filas de `party` ya referenciadas: una misma clave resuelve siempre a la misma fila dentro de la carga y entre cargas.

## R13

`docs/ingestor/ingesta.md` DEBE describir, en el paso de plata de «Comportamiento de `ingest-polls`», que el adaptador resuelve los rótulos de columna contra el catálogo `data/party_catalog.toml` y que el loader convierte cada clave en fila con la resolución compartida de `parties.py` (catálogo → nombre existente → alta con warning).

## R14

`docs/ingestor/ingesta.md` NO DEBE describir el mapeo de partidos de los sondeos como una tabla de slugs propia del adaptador (la expresión «slugs del mapeo» no aparece en el documento).

## R15

La feature DEBE quedar cubierta por tests en `ingestor/tests/test_party_polls.py` (adaptador, loader y coincidencia sondeos↔elecciones), sin red, y por la actualización de los tests afectados de `test_wikipedia_polls.py` y `test_polls_load.py`; los tests del adaptador NO DEBEN necesitar base de datos.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «el adaptador de sondeos resuelve los rótulos de columna contra el catálogo compartido (los 15 actuales + altas nuevas con warning); PARTY_COLUMNS se sustituye» | R1, R2, R3, R4, R5, R6, R7, R8, R9, R10 |
| «test de coincidencia sondeos↔resultados por marca (misma fila de party para poll_result y party_election)» | R11, R12, R15 |
| «documentación del mapeo de sondeos actualizada (sustitución documentada)» | R13, R14 |

## Nota de verificación

- R1, R2, R5: `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog` — con el catálogo real, las quince etiquetas resuelven a los slugs fijados y cada slug resuelve a su propia ficha; `::test_parse_resolves_label_outside_mapping` — una etiqueta con ficha pero fuera de las quince (p. ej. `C's`) produce la clave del slug de la ficha y no avisa.
- R3, R4: `test_wikipedia_polls.py::test_unknown_column_warns_and_kept` — con un catálogo explícito de `tmp_path` (sin ficha para la etiqueta): clave = rótulo crudo y warning `unknown party column`.
- R6: `test_wikipedia_polls.py::test_mapping_table_removed` — el módulo no expone `PARTY_COLUMNS` ni `PartyColumn`.
- R7: `test_wikipedia_polls.py::test_module_is_stdlib_only_and_pure` (actualizado: el conjunto de imports de `ingestor` admite `ingestor.parties`).
- R8: `test_party_polls.py::test_loader_resolves_catalog_only_label` — columna `C's` → fila de la ficha, sin `unknown party column` ni `unknown party label`; `test_polls_load.py::test_cli_registers_and_loads` — los nombres de las filas creadas salen de las fichas del catálogo.
- R9: `test_party_polls.py::test_loader_has_no_local_party_mapping` — el módulo del loader no expone `_PARTY_NAMES` ni `_party_slug`.
- R10: `test_polls_load.py::test_unknown_label_creates_party_with_warning` — alta con warning `unknown party label`, `name` literal y reutilización en la segunda carga.
- R11: `test_party_polls.py::test_poll_and_election_share_party_row` — proceso con cabecera `B.N.G.` + sondeo con columna `BNG`: una sola fila `bng` y el mismo `party_id` en `party_election` y `poll_result`.
- R12: `test_polls_load.py::test_existing_party_and_pollster_reused` y `::test_unknown_label_creates_party_with_warning` (segunda carga) — la fila se reutiliza por `id`; el test de coincidencia reingiere un segundo snapshot y el conteo de `party` no crece.
- R13, R14: `test_party_polls.py::test_docs_ingesta_polls_mapping` — subcadenas `parties.py` y `party_catalog.toml` dentro de la sección «Comportamiento de `ingest-polls`», y ausencia de «slugs del mapeo» en el documento.
- R15: los tres ficheros de test citados; los del adaptador no importan `conftest` ni sesiones de base de datos.

## Notas de alcance

- **La sustitución cambia el camino, no el contrato de `PollRow.results`**: las claves siguen siendo el slug de `silver.party` para columnas con ficha y el rótulo crudo para las que no la tienen.
- **`.agents/data-sources.md` no se toca**: su sección de sondeos describe la fuente (formato de la página, rarezas y licencia), no el mapeo de identidad; el mapeo vive en `docs/ingestor/ingesta.md`.
- **No hay recarga obligatoria del snapshot real como acceptance**: la sustitución se prueba en los esquemas de test; la comprobación sobre el `silver` local es evidencia del implementer (tarea de `tasks.md`).
- **El catálogo no se re-redacta**: las fichas son de la feature 12; si una marca no resuelve, el bucle es alias en `data/party_catalog.toml` + recarga del snapshot.
