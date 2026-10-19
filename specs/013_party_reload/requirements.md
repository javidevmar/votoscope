# Requisitos — `party_reload`

Feature `id 13` de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`). Depende de la feature 12 ([`specs/012_party_catalog/`](../012_party_catalog/)): el catálogo `ingestor/src/ingestor/data/party_catalog.toml` y el módulo `ingestor/src/ingestor/parties.py` (`normalize`, `slugify`, `Catalog`, `load_catalog`, `PartyResolver`).

Alcance: (a) integrar la resolución compartida en el loader de elecciones —`_resolve_parties` de `ingestor/src/ingestor/elections/loaders/election.py` deja el slug provisional por siglas—, (b) ejecutar la recarga `--force` de los 13 procesos locales de `data/raw/congreso/`, con las comprobaciones de identidad y la limpieza de huérfanos, y (c) poner al día los documentos que describen la identidad de `party`. El adaptador y el loader de sondeos llegan en la feature 14.

Contexto (diagnóstico absorbido): la identidad de `party` sale del slug de las siglas de la cabecera nacional del `03`, así que la misma marca con otra grafía en otro año crea fila nueva (`B.N.G.`/`BNG`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `P.P.`/`PP`, `C's`/`Cs`…): 27 grupos de filas con el mismo nombre salvo puntuación (55 filas) sobre 549 filas de `party`, y en el 2023 del MVP BNG, UPL y FIA caen en la fila punteada. La recarga con el catálogo deja cada marca en una fila.

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican): `party` y `party_election` valen tal cual y `silver` se recalcula reingiriendo. Sin dependencias nuevas. Sin excepciones nuevas (`IngestError`). Sin cambios de CLI.

## R1

CUANDO se ingiere una elección, el sistema DEBE resolver cada cabecera nacional de candidatura del fichero `03` con la resolución compartida de `parties.py` (`PartyResolver`: catálogo → nombre existente → alta con warning), en lugar del slug provisional por siglas.

## R2

CUANDO dos procesos publican la misma marca con siglas que difieren solo en puntuación (`B.N.G.` y `BNG`), el sistema DEBE dejarla en una única fila de `silver.party`, referenciada por las candidaturas de ambos procesos.

## R3

CUANDO la etiqueta de una cabecera nacional tiene ficha en el catálogo, el sistema DEBE resolverla a la fila de `party` del slug de la ficha sin registrar `unknown party label`.

## R4

CUANDO la etiqueta no tiene ficha ni coincide con el nombre normalizado de una fila existente, el sistema DEBE crear la fila y registrar el warning `unknown party label: <etiqueta> -> <slug>`.

## R5

CUANDO se recarga una elección ya procesada (`--force`), el sistema DEBE reutilizar las filas de `party` existentes sin crear duplicados.

## R6

CUANDO se recarga una elección ya procesada (`--force`), el sistema DEBE re-derivar sus hechos de los mismos ficheros conservando los conteos de `vote`, `turnout` y `party_election`.

## R7

CUANDO se ejecuta `uv run ingestor ingest ../data/raw/congreso --force` sobre los 13 procesos locales, el sistema DEBE dejar los 13 procesos —cada uno con candidaturas y hechos— en `silver`.

## R8

El estado de `silver.party` tras la recarga y la limpieza de huérfanos NO DEBE contener ningún grupo de dos o más filas cuyos nombres coincidan al ignorar mayúsculas y puntuación (0 filas en la consulta de grupos por puntuación de [`design.md`](design.md) §«Comprobaciones»).

## R9

Tras la recarga, cada una de las marcas `BNG`, `UPL`, `FIA`, `Cs`, `PP`, `PSOE` e `IU` DEBE tener exactamente una fila en `silver.party` (ignoradas mayúsculas y puntuación del nombre).

## R10

La limpieza de huérfanos DEBE dejar `silver.party` sin filas que no tengan ni candidaturas (`party_election`) ni resultados de sondeo (`poll_result`), preservando las referenciadas por `poll_result`.

## R11

`.agents/data-model.md` DEBE describir la identidad de `party` como resuelta por `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo → nombre existente → alta con warning).

## R12

`.agents/data-model.md` NO DEBE describir la agrupación de `party` como provisional ni como pendiente de curar.

## R13

`docs/ingestor/ingesta.md` DEBE describir, en el paso de candidaturas de «Comportamiento de `ingest`» y en la tabla «Qué queda en `silver`», la resolución de `party` por `parties.py` sobre `data/party_catalog.toml`.

## R14

`docs/ingestor/ingesta.md` NO DEBE describir la fila de `party` como identidad provisional.

## R15

`ingestor/AGENTS.md` DEBE listar `src/ingestor/parties.py` y `src/ingestor/data/party_catalog.toml` entre los ficheros del paquete.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «el loader de elecciones resuelve por parties.py (misma marca → una fila; test con siglas punteadas → un solo party)» | R1, R2, R3, R4 |
| «ingest --force de los 13 procesos locales; comprobaciones de curación en verde (0 grupos por puntuación; BNG/UPL/FIA/Cs/PP/PSOE/IU en una fila)» | R7, R8, R9 |
| «huérfanos borrados; hechos intactos salvo el party_id de las candidaturas fusionadas» | R5, R6, R10 |
| «docs al día: .agents/data-model.md, docs/ingestor/ingesta.md, ingestor/AGENTS.md» | R11, R12, R13, R14, R15 |

## Nota de verificación

- R1–R3: `ingestor/tests/test_party_reload.py::test_two_processes_one_party` — dos procesos sintéticos (2008 con `B.N.G.`, 2019 con `BNG`) en los esquemas de test (fixture `db`, sin `data/raw` ni red): una sola fila `party` (slug del catálogo), dos `party_election` con el mismo `party_id` y sin warning.
- R4: `::test_unknown_head_label_warns` — proceso sintético con `PARTIDO SIN FICHA`: fila nueva con el literal y warning con su slug.
- R5, R6: `::test_force_reload_preserves_facts` — segunda pasada `--force` sobre los mismos procesos: la fila `party` no se duplica (mismo `id`) y los conteos de `vote`/`turnout`/`party_election` no cambian.
- R7–R10: verificación operativa con el SQL de [`design.md`](design.md) §«Comprobaciones», registrada en `progress/impl_party_reload.md`; sin test automatizado.
- R11–R15: `test_docs_data_model` (R11, R12 — subcadenas y ausencia de «provisional»), `test_docs_ingesta` (R13, R14 — ídem) y `test_docs_ingestor_agents` (R15).

## Notas de alcance

- **No redacta catálogo**: las fichas son de la feature 12. Si la recarga destapara un par de grafías sin resolver (no esperado: el catálogo cubre las marcas del 2023 y las familias, y el resto casa por nombre), el bucle es alias en el catálogo + reingesta de los procesos afectados; el diff del catálogo es el registro de cada decisión.
- **La recarga no toca los ficheros fuente** (`data/raw/` es inmutable) ni los sondeos: `ingest-polls` no se ejecuta aquí (feature 14).
- **Los slugs de las filas fusionadas desaparecen** (p. ej. el punteado): hoy nadie los consume (no hay `gold` ni web todavía) y los sondeos se recargan en la feature 14.
- **La limpieza de huérfanos es operación de mantenimiento** (SQL revisable), no parte del loader: un borrado automático en la ingesta podría llevarse una marca referenciada por `poll_result` de otro dominio.
- **Los avisos de la recarga** (altas sin ficha) son la cola de curación; con el catálogo de la 12 se esperan pocos o ninguno, y el informe de implementación registra los que aparezcan.
