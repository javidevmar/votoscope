# Requisitos — `party_catalog`

Feature `id 12` de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`). Alcance: crear `ingestor/src/ingestor/data/party_catalog.toml` —fichas de marca electoral: `name` y `aliases` con literales ya ingeridos— y `ingestor/src/ingestor/parties.py` —normalización de etiquetas, catálogo y resolución compartida `catálogo → nombre existente → alta con warning`—, con sus tests. **No integra los loaders** (eso es de las features 13 y 14): su única intervención en código existente es unificar `slugify` en `parties.py`.

Contexto (diagnóstico de la iniciativa, absorbido): hoy la identidad de `party` se deriva de las siglas de la cabecera nacional del `03` (slug de las siglas), de modo que la misma marca con otra grafía en otro año crea fila nueva (`B.N.G.`/`BNG`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `P.P.`/`PP`…); además, los rótulos de los sondeos (`PARTY_COLUMNS` de `polls/adapters/wikipedia_polls.py`) y las siglas de las elecciones no comparten identidad. Esta feature crea la identidad canónica compartida (catálogo curado en el repo + resolución única); la recarga de `silver` con el catálogo y la sustitución del mapeo de sondeos llegan en las features 13 y 14.

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican): `party` y `party_election` valen tal cual. Sin dependencias nuevas (`tomllib` es de la stdlib; el proyecto requiere Python ≥ 3.12). Sin excepciones nuevas (`IngestError`).

## R1

El sistema DEBE implementar en `src/ingestor/parties.py` la función `normalize(label: str) -> str`, que devuelve la clave normalizada de una etiqueta: NFKD plegado, sin marcas diacríticas (incluidas las de `ç` y `ñ`), sin caracteres no alfanuméricos y en mayúsculas (`B.N.G.`→`BNG`, `C's`→`CS`, `P. RIOJANO`→`PRIOJANO`, `EH Bildu`→`EHBILDU`, `Aliança.cat`→`ALIANCACAT`).

## R2

El sistema DEBE implementar `load_catalog(path: Path = <ruta del paquete>) -> Catalog`: leer con `tomllib` un fichero TOML con la tabla `[parties]` —clave: slug canónico; por ficha, `name` obligatorio y `aliases` opcional— y devolver un `Catalog` con una ficha por slug.

## R3

El `Catalog` DEBE resolver `lookup(label)` contra las claves normalizadas del `name` y de los `aliases` de sus fichas (la clave de `label` es `normalize(label)`).

## R4

SI ninguna clave normalizada del catálogo coincide con la etiqueta ENTONCES `lookup` DEBE devolver `None`.

## R5

SI dos fichas distintas reclaman la misma clave normalizada (nombre o alias) ENTONCES `load_catalog` DEBE lanzar `IngestError` indicando la clave en conflicto.

## R6

SI la clave normalizada de un alias coincide con la del `name` de su propia ficha ENTONCES `load_catalog` DEBE lanzar `IngestError` (los alias solo existen para grafías que no coinciden por normalización).

## R7

SI el `name` o un alias de una ficha no contiene ningún carácter alfanumérico ENTONCES `load_catalog` DEBE lanzar `IngestError`.

## R8

SI el fichero del catálogo no existe o no es TOML válido ENTONCES `load_catalog` DEBE lanzar `IngestError` con la ruta del fichero.

## R9

SI una ficha del catálogo no declara `name` ENTONCES `load_catalog` DEBE lanzar `IngestError` con el slug de la ficha.

## R10

El catálogo DEBE resolver las quince etiquetas de `PARTY_COLUMNS` (`polls/adapters/wikipedia_polls.py`) a los slugs que ese mapeo fija: `PP`→`pp`, `PSOE`→`psoe`, `Vox`→`vox`, `Sumar`→`sumar`, `ERC`→`erc`, `Junts`→`jxcat-junts`, `EH Bildu`→`eh-bildu`, `PNV`→`eaj-pnv`, `BNG`→`bng`, `CCa`→`cca`, `UPN`→`u-p-n`, `Adelante Andalucía (2021)`→`adelante-andalucia`, `Podemos`→`podemos`, `SALF`→`salf`, `Aliança.cat`→`alianca-cat`.

## R11

Las fichas `salf` y `alianca-cat` DEBEN usar como `name` los literales que fija el adaptador de sondeos: «Se Acabó La Fiesta» y «Aliança Catalana».

## R12

Cada `name` de `party` del proceso del 23-jul-2023 ingerido en `silver` (volcado literal en `ingestor/tests/fixtures/party_catalog/brands_2023.txt`) DEBE resolver a una ficha del catálogo.

## R13

Las grafías punteadas del diagnóstico DEBEN resolver a la misma ficha que sus grafías limpias: `B.N.G.`/`BNG`, `P.P.`/`PP`, `P.S.O.E.`/`PSOE`, `C's`/`Cs`, `I.U.`/`IU`, `P.C.P.E.`/`PCPE`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `D.N.`/`DN`, `A.u.N.`/`AUN`.

## R14

Cada una de las grafías de las familias del diagnóstico DEBE resolver a una ficha del catálogo: `podemos`, `unidas podemos`, `lv`, `lve`, `lv-gv`, `verdes`, `fe-de-las-j`, `fe-de-las-jons`, `fe-jons`, `na`, `na-bai`, `erc`, `esquerra`, `erc-catsi`.

## R15

CUANDO se resuelven `Podemos`, `Unidas Podemos` y `Sumar`, el sistema DEBE devolver tres slugs distintos (las coaliciones con nombre propio no se fusionan).

## R16

La resolución DEBE usar solo igualdad exacta de claves normalizadas o clave de alias explícita, y NO DEBE usar coincidencia aproximada (`PPX` no resuelve a `pp`).

## R17

CUANDO se resuelve una etiqueta con ficha en el catálogo, el sistema DEBE devolver la fila de `party` con el slug de la ficha, creándola como `Party(name=<name de la ficha>, slug=<slug de la ficha>)` si no existe.

## R18

La creación de una fila por ficha del catálogo NO DEBE registrar ningún warning.

## R19

CUANDO la etiqueta no tiene ficha en el catálogo y coincide por normalización con el `name` de filas de `party` existentes, el sistema DEBE devolver una de esas filas existentes.

## R20

CUANDO varias filas existentes coinciden por nombre normalizado, el sistema DEBE elegir la que tenga `slug` igual a `slugify(clave normalizada)`.

## R21

SI ninguna de las filas coincidentes tiene ese slug ENTONCES el sistema DEBE elegir la de `id` menor.

## R22

CUANDO no hay ficha ni coincidencia por nombre, el sistema DEBE crear `Party(name=<etiqueta literal>, slug=slugify(<etiqueta>) recortado a 60 caracteres)`.

## R23

SI el slug calculado ya está en uso ENTONCES el sistema DEBE resolver la colisión con el sufijo `-<code>` (cuando el llamador pase un código) o con el primer sufijo numérico libre (`-2`, `-3`, …) cuando no lo pase.

## R24

CUANDO se crea una fila por el camino de alta sin ficha, el sistema DEBE registrar un warning con la forma `unknown party label: <etiqueta> -> <slug>`.

## R25

CUANDO un mismo resolver resuelve dos veces la misma etiqueta —o dos etiquetas que resuelven a la misma fila—, el sistema DEBE devolver una única fila, sin crear duplicados.

## R26

El sistema DEBE exponer una única implementación de `slugify` en `parties.py`, importada por `elections/loaders/election.py` y `polls/loaders/polls.py` — sin copias locales.

## R27

El módulo `parties.py` DEBE implementarse solo con la biblioteca estándar (incluido `tomllib`) y `ingestor.models`/`ingestor.errors`, sin dependencias nuevas en `ingestor/pyproject.toml`.

## R28

El sistema DEBE cubrir el catálogo y el resolver con tests en `ingestor/tests/test_parties.py`, sin red ni base de datos, incluida la fixture `ingestor/tests/fixtures/party_catalog/brands_2023.txt`.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «`src/ingestor/data/party_catalog.toml` con las fichas redactadas desde silver: las 15 etiquetas de sondeos, las marcas del 2023 y las familias del diagnóstico» | R2, R10, R11, R12, R13, R14, R15 (proceso de extracción y redacción en `design.md` §Curación) |
| «`src/ingestor/parties.py` con la precedencia catálogo → nombre existente → alta (slugify) + warning; sin fuzzy-matching» | R1, R3, R16, R17, R18, R19, R20, R21, R22, R23, R24 |
| «tests: normalización (NFKD), precedencia, desempates y altas con warning; integridad del catálogo (slugs y alias únicos; las 15 etiquetas cubiertas)» | R1, R5, R6, R7, R10, R16–R25, R28 |
| «sin dependencias nuevas (tomllib de la stdlib)» | R27 |
| Extra: validación del catálogo como configuración (fallo claro si está roto) | R4, R5, R6, R7, R8, R9 |
| Extra: una sola `slugify` compartida con los loaders | R26 |
| Extra: alcance acotado — el catálogo no tiene que ser exhaustivo | Nota de alcance |

## Nota de verificación

- R1: matriz de `normalize` (puntuación, diacríticos `ç`/`ñ`, espacios, mayúsculas, claves vacías).
- R2, R3, R4, R8, R9: `load_catalog`/`lookup` con TOML de `tmp_path`; la ruta por defecto se ejerce con el fichero real.
- R5, R6, R7: TOML inválidos de `tmp_path` → `IngestError`; el fichero real se comprueba además con el test de integridad (claves únicas, sin alias redundantes).
- R10, R11, R13, R14, R15: catálogo real, listas de etiquetas fijas de este documento.
- R12: fixture `brands_2023.txt` (volcado de la extracción de `design.md` §Curación) — cada línea resuelve.
- R16–R25: `PartyResolver` con filas `Party` transitorias y catálogos de `tmp_path` (sin base de datos).
- R26: identidad `election.slugify is parties.slugify is polls.slugify` (los tres módulos exponen el mismo objeto) y casos de `slugify`.
- R27: análisis de los imports del módulo (solo stdlib y `ingestor.*`) y de `ingestor/pyproject.toml` (las cuatro dependencias aprobadas, ninguna más).
- R28: las tests viven en `ingestor/tests/test_parties.py` y no importan red ni sesiones de base de datos.

## Notas de alcance

- **No integra los loaders**: `_resolve_parties` de elecciones (feature 13) y de sondeos (feature 14) pasarán a usar `parties.py` en sus propias features; aquí el módulo queda cubierto por tests propios.
- **Alcance de la curación**: las 15 etiquetas de sondeos (R10), las marcas del 2023 (R12) y las familias del diagnóstico (R13–R15). Los micro-partidos de un solo proceso fuera de ese alcance NO necesitan ficha: caen por la vía de coincidencia por nombre (R19).
- **Criterio de identidad** (de la iniciativa): continuidad de la marca electoral; grafías de la misma marca se fusionan (por normalización o alias) y las coaliciones con nombre propio no (R15). Las decisiones de las familias se registran en el diff del catálogo —criterio detallado en `design.md` §Curación—; ante la duda, no fusionar.
- **Los `name` y `aliases` se copian literalmente** de lo ingerido en `silver` (extracción de `design.md`), salvo los literales de `salf`/`alianca-cat` (R11). La fidelidad de la extracción la revisa el humano en el diff del catálogo y queda documentada en `progress/impl_party_catalog.md`.
- **No toca el modelo ni el CLI**: sin cambios en `docs/db/schema.drawio`, `models.py`, Alembic ni comandos; `party.color` sigue fuera (se curará con `gold`).
- **Documentación**: esta feature no cambia cómo funciona la ingesta, así que `docs/ingestor/ingesta.md`, `ingestor/AGENTS.md` y `.agents/data-model.md` se actualizan en la feature 13, cuando el loader resuelva por catálogo (su `acceptance` lo exige).
