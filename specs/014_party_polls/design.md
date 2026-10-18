# Diseño — `party_polls`

Feature 14 de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`), redactada absorbiendo el diseño de la iniciativa. Depende de la feature 12 ([`specs/012_party_catalog/`](../012_party_catalog/)): el catálogo `ingestor/src/ingestor/data/party_catalog.toml` y el módulo `ingestor/src/ingestor/parties.py` (`normalize`, `slugify`, `Catalog`, `load_catalog`, `PartyResolver`; interfaz exacta en su §«Firmas nuevas» y §«Interfaz para las features 13 y 14»); y de la feature 13 ([`specs/013_party_reload/`](../013_party_reload/)), que dejó el loader de elecciones resolviendo por `parties.py` y las fixtures sintéticas `ingestor/tests/fixtures/party_reload/`.

Alcance: (a) el adaptador de sondeos resuelve sus rótulos de columna contra el catálogo y pierde `PARTY_COLUMNS`/`PartyColumn`, (b) el loader de sondeos resuelve sus claves con `PartyResolver` y pierde `_PARTY_NAMES`/`_party_slug`, (c) el test de coincidencia `poll_result` ↔ `party_election` por marca y (d) la puesta al día de `docs/ingestor/ingesta.md` §«Comportamiento de `ingest-polls`».

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica); `party` y `poll_result` valen tal cual y `silver` se recalcula reingiriendo. Sin dependencias nuevas. Sin excepciones nuevas (`IngestError`, ya usada por `load_catalog`). Sin CLI. Sin firmas públicas nuevas.

## Estado observado al redactar (2026-10-18, sobre el código de las features 8 y 9)

- `polls/adapters/wikipedia_polls.py`: `PartyColumn` + `PARTY_COLUMNS` (quince rótulos → slug/nombre), `_column_plan` decide por `label in PARTY_COLUMNS` y, para el resto, avisa `unknown party column` y usa el rótulo crudo como clave; `parse_polls(wikitext)` no recibe catálogo.
- `polls/loaders/polls.py`: `_PARTY_NAMES` (slug → nombre, derivado de `PARTY_COLUMNS`), `_party_slug(key)` (slug del mapeo o `slugify` del rótulo crudo) y `_resolve_parties` con get-or-create por slug + warning `unknown party label: %s -> %s`. La feature 13 ya apunta el import de `slugify` a `ingestor.parties`.
- Tests que tocan el mapeo: `test_wikipedia_polls.py::test_party_columns_mapping` (contrato de `PARTY_COLUMNS`), `::test_unknown_column_warns_and_kept`, `::test_module_is_stdlib_only_and_pure` (imports de `ingestor` limitados a `ingestor.polls.parsers.wikitext`); `test_polls_load.py::test_cli_registers_and_loads` (nombres literales `Partido Popular`, `Partido Socialista Obrero Español`), `::test_unknown_label_creates_party_with_warning`, `::test_docs_ingesta`.
- `docs/ingestor/ingesta.md`, paso 6 de «Comportamiento de `ingest-polls`»: «…get-or-create de `pollster` (por el slug de la firma) y de `party` (slugs del mapeo; un rótulo desconocido de una columna nueva se da de alta con su slug y un warning)…».
- Estado local de referencia (observado en [`specs/013_party_reload/`](../013_party_reload/) §«Estado observado»): 575 `poll`, 6.125 `poll_result`; el único rótulo fuera de las quince es `FA` (columna sin filas de datos en el alcance actual), que el adaptador conserva con rótulo crudo y el loader da de alta con warning.

## Decisión

- **Una sola fuente de identidad**: los rótulos de los sondeos resuelven con el catálogo de la 12 y las claves acaban en filas con el mismo `PartyResolver` que usa el loader de elecciones (feature 13). `PARTY_COLUMNS` y `_PARTY_NAMES` desaparecen: eran una segunda tabla de identidad que podía divergir del catálogo.
- **El adaptador consulta, no crea**: `wikipedia_polls.py` resuelve cada rótulo con `Catalog.lookup(label)` y emite el `slug` de la ficha; sin ficha, conserva el rótulo crudo y avisa (convención de la feature 8, intacta). El adaptador no toca la base de datos: quien crea o reutiliza filas es el loader.
- **El loader delega la identidad**: `_resolve_parties` construye un `PartyResolver` con las filas `Party` existentes y el catálogo (`load_catalog()`) y resuelve cada clave; el warning de alta lo emite el resolver (R24 de la 12), no el loader.
- **El contrato de `PollRow.results` no cambia**: clave = slug de `silver.party` (ficha del catálogo) o rótulo crudo. Los fixtures, los tests de la feature 11 y el cotejo siguen leyendo las mismas claves; los quince rótulos conservan sus slugs (R10 de la 12).
- **Sin fuzzy-matching** (heredado de la 12): normalización exacta o alias explícito; si una marca no resuelve, el bucle es alias en `data/party_catalog.toml` + recarga del snapshot.

## Archivos

| Acción | Archivo |
| --- | --- |
| modificar | `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py` — resolución por `Catalog`; fuera `PartyColumn`/`PARTY_COLUMNS`; `parse_polls(wikitext, catalog=None)` |
| modificar | `ingestor/src/ingestor/polls/loaders/polls.py` — `_resolve_parties` por `PartyResolver`/`load_catalog`; fuera `_PARTY_NAMES`/`_party_slug` |
| modificar | `ingestor/tests/test_wikipedia_polls.py` — contrato del adaptador (§«Tests») |
| modificar | `ingestor/tests/test_polls_load.py` — nombres por catálogo (§«Tests») |
| crear | `ingestor/tests/test_party_polls.py` — R8, R9, R11, R12, R13, R14, R15 |
| modificar | `docs/ingestor/ingesta.md` — paso 6 de «Comportamiento de `ingest-polls`» (§«Documentos») |
| crear | `progress/impl_party_polls.md` — evidencia de la recarga y trazabilidad R ↔ test (convención del arnés; no es un artefacto del acceptance) |

No se tocan: `.agents/data-model.md` (la identidad de `party` la describió la 13), `.agents/data-sources.md` (describe la fuente, no el mapeo), `ingestor/AGENTS.md` (el bullet del adaptador —«secciones y tablas por año, cabecera, partidos»— sigue siendo cierto), `models.py`, Alembic y `docs/db/schema.drawio`.

## Código

### Adaptador — `polls/adapters/wikipedia_polls.py`

```python
from ingestor.parties import Catalog, load_catalog


def parse_polls(wikitext: str, catalog: Catalog | None = None) -> list[PollRow]:
    """Polls of every year table of the page, in page order."""
    catalog = load_catalog() if catalog is None else catalog
    return [
        row
        for year, table in poll_tables(wikitext)
        for row in _read_table(table, year, catalog)
    ]


def _column_plan(label_cells: list[Cell], catalog: Catalog) -> _Plan | None:
    ...
    for index, label in enumerate(labels):
        if label in FIXED_COLUMNS:
            fixed[label] = index
        elif label == LEAD_COLUMN:
            continue
        else:
            entry = catalog.lookup(label)
            if entry is None:
                logger.warning("unknown party column: %s", label)
                parties[index] = label
            else:
                parties[index] = entry.slug
    return _Plan(fixed=fixed, parties=parties)
```

- `_read_table(table, year, catalog)` propaga el catálogo; `_read_row` y el resto no cambian.
- El parámetro opcional hace inyectable el catálogo en los tests (TOML de `tmp_path`); el loader sigue llamando `parse_polls(texto)` y usa el catálogo del paquete.
- `PartyColumn` y `PARTY_COLUMNS` se borran; el docstring del módulo deja de decir «stdlib only» a secas: sigue sin red ni base de datos, pero lee el catálogo empaquetado vía `load_catalog()` (una lectura de fichero, no de la BD).
- `_Plan` pasa a documentar: «a party key is the catalogue slug of a labelled column or the raw label of an unknown one; the loader resolves its identity».

### Loader — `polls/loaders/polls.py`

```python
from ingestor.parties import PartyResolver, load_catalog, slugify


def _resolve_parties(session: Session, rows: list[PollRow]) -> dict[str, int]:
    """Resolve every result key (catalogue slug or raw label) to a party row."""
    keys = {key for row in rows for key in row.results}
    resolver = PartyResolver(session.scalars(select(Party)), load_catalog())
    parties = {key: resolver.resolve(key) for key in keys}
    for party in set(parties.values()):
        session.add(party)  # no-op when the row was already persistent
    session.flush()
    return {key: party.id for key, party in parties.items()}
```

- `load_polls` usa `party_ids[key]` directamente en `result_rows` (desaparece `_party_slug`); `_resolve_pollsters` no cambia (su `slugify` ya viene de `ingestor.parties` desde la 13).
- Un `PartyResolver` por carga: una lectura completa de `Party` por snapshot. El resolver indexa las filas que crea, así que dos claves que llevan a la misma ficha devuelven el mismo objeto (R25 de la 12) y `party_ids` queda consistente.
- El warning de alta lo emite el resolver con el formato fijado por la 12 (`unknown party label: %s -> %s`); el `logger.warning` del loader desaparece. Un rótulo crudo como `FA` sigue su camino actual: columna avisada por el adaptador, alta avisada por el resolver.

### Contrato de claves (por qué `resolve(slug)` encuentra la ficha)

Las claves que emite el adaptador son slugs de fichas del catálogo; `PartyResolver.resolve` las pasa por `Catalog.lookup`, que busca por `normalize(clave)`. El diseño se apoya en un invariante del catálogo de la 12: **para toda ficha, `lookup(<slug>)` devuelve esa ficha** (su `name` o un alias colisiona en clave normalizada con el slug normalizado; las quince lo cumplen por construcción —`PP`/`P.P.`→`pp`, `CCa`→`cca`, `SALF`→`salf`, `Aliança.cat`→`alianca-cat`…). El test `test_party_labels_resolve_through_catalog` lo fija para las quince; si alguna fallara, la corrección es un alias en `data/party_catalog.toml` (bucle de la 12), nunca código.

| Caso | Clave del adaptador | Camino del loader | Resultado |
| --- | --- | --- | --- |
| Rótulo con ficha (`Junts`) | `jxcat-junts` | `lookup` → ficha → fila por slug o creación con el `name` de la ficha | fila `jxcat-junts`, sin warning |
| Rótulo crudo de una columna sin ficha (`FA`) | `FA` | sin ficha ni nombre coincidente → alta `Party(name="FA", slug="fa")` | fila nueva + warning `unknown party label` |
| Clave repetida en la carga (dos columnas → misma ficha) | una sola clave | un único objeto del resolver | una fila por carga y entre cargas |

## Warnings (subcadenas estables para `caplog`)

| Subcadena | Origen | Caso | R |
| --- | --- | --- | --- |
| `unknown party column` | adaptador (`wikipedia_polls.py`) | columna sin ficha en el catálogo | R4 |
| `unknown party label` | resolver (`parties.py`), vía loader | alta sin ficha | R10 |

Un rótulo crudo acumula los dos avisos (deriva de la fuente y alta sin ficha), igual que hoy. Las quince etiquetas cubiertas no avisan por ninguno de los dos.

## Tests

### `ingestor/tests/test_wikipedia_polls.py` (modificar)

| Test | Acción | Cubre |
| --- | --- | --- |
| `test_party_labels_resolve_through_catalog` | sustituye a `test_party_columns_mapping`: con `load_catalog()`, las quince etiquetas → slugs fijados; `lookup(<slug>)` devuelve la ficha del slug; nombres fijados de `salf`/`alianca-cat` | R1, R2, R5 |
| `test_parse_resolves_label_outside_mapping` | nuevo: tabla inline con una etiqueta con ficha pero fuera de las quince (`C's`) → clave = slug de la ficha (`catalog.lookup("C's").slug`) y sin `unknown party column` | R1, R2 |
| `test_unknown_column_warns_and_kept` | adaptado: `parse_polls(fixture, catalog=load_catalog(<TOML mínimo de tmp_path>))` → clave cruda `FA` y warning | R3, R4 |
| `test_mapping_table_removed` | nuevo: el módulo no expone `PARTY_COLUMNS` ni `PartyColumn` | R6 |
| `test_module_is_stdlib_only_and_pure` | actualizado: los imports de `ingestor` admiten `{ingestor.polls.parsers.wikitext, ingestor.parties}` | R7 |

`test_synthetic_columns_mapping`, `test_color_header_row_ignored`, `test_lead_column_ignored_without_warning` y el resto de la suite del adaptador quedan verdes sin cambios: las claves del fixture `synthetic_columns.wikitext` (`vox`, `pp`, `salf`, `alianca-cat`, `adelante-andalucia`, `FA`) son las mismas con el catálogo.

### `ingestor/tests/test_polls_load.py` (modificar)

| Test | Acción | Cubre |
| --- | --- | --- |
| `test_cli_registers_and_loads` | los nombres de `pp`/`psoe` se contrastan con `load_catalog().lookup("PP"/"PSOE").name` (el literal lo fija la curación de la 12, no este test); `salf` mantiene «Se Acabó La Fiesta» (R11 de la 12) | R8 |
| `test_existing_party_and_pollster_reused` · `test_replacement_deletes_previous_polls` · `test_unknown_label_creates_party_with_warning` | sin cambios: reutilización por `id`, conteo de slugs y alta con warning siguen valiendo con el resolver | R10, R12 |

### `ingestor/tests/test_party_polls.py` (nuevo; fixture `db` de `conftest.py`)

| Test | Qué fija | Cubre |
| --- | --- | --- |
| `test_loader_resolves_catalog_only_label` | snapshot inline con columnas `("PP", "C's")`: filas de las fichas, sin `unknown party column` ni `unknown party label` (en rojo antes de la sustitución: hoy `C's` avisa) | R8 |
| `test_loader_has_no_local_party_mapping` | el módulo del loader no expone `_PARTY_NAMES` ni `_party_slug` | R9 |
| `test_poll_and_election_share_party_row` | ingesta de `fixtures/party_reload/02200806` (cabecera `B.N.G.`, de la 13) + snapshot con columna `BNG` y columna `PP`: una sola fila `bng` y `party_election.party_id == poll_result.party_id`; segunda carga con otra revisión no duplica `party` | R11, R12 |
| `test_docs_ingesta_polls_mapping` | subcadenas `parties.py` y `party_catalog.toml` dentro de la sección «Comportamiento de `ingest-polls`» (extraída del documento), y «slugs del mapeo» ausente | R13, R14 |

Detalles que fijan el contrato:

- Helpers mínimos en el fichero nuevo (duplicados de los de `test_polls_load.py`/`party_reload`): `_seed_geography(db)`, `_table(...)` para el wikitexto inline, `_write_snapshot(tmp_path, revid, wikitext)` y la copia de las fixtures de elección a `tmp_path` (bronce). Sin ficheros de fixture nuevos.
- `test_poll_and_election_share_party_row` es un test de **contrato**: la propiedad debe valer antes y después de la sustitución (hoy ambas rutas coinciden en `bng` por casualidad de slug), y su valor es impedir que la sustitución la rompa. El que sí nace en rojo es `test_loader_resolves_catalog_only_label`.
- La segunda carga del test de contrato usa una revisión mayor para pasar el guard; se contrasta `count(*)` de `party` antes y después.
- Sin red y sin `data/raw/`: el adaptador se prueba sin base de datos; los tests de loader usan los esquemas de test.

## Documentos

- **`docs/ingestor/ingesta.md`** — paso 6 de «Comportamiento de `ingest-polls`», sustituyendo el paréntesis del mapeo:

  ```markdown
  6. **Plata (una transacción)**: get-or-create de `pollster` (por el slug de la firma) y de
     `party`: el adaptador resuelve cada rótulo de columna contra el catálogo
     `data/party_catalog.toml` y el loader convierte cada clave en fila con la resolución
     compartida de `parties.py` (catálogo → nombre existente → alta con warning); un rótulo
     sin ficha se conserva con su literal y el resolver lo da de alta con un warning.
     **Borrado total** de `poll`/`poll_result` e inserción de las filas del snapshot.
     `silver` refleja el último snapshot ingerido; el histórico de revisiones vive en bronce.
  ```

- Subcadenas que fija `test_docs_ingesta_polls_mapping`: `parties.py` y `party_catalog.toml` presentes en la sección «Comportamiento de `ingest-polls`», «slugs del mapeo» ausente del documento. El test acota la búsqueda a la sección (no al documento entero): la 13 ya introduce esas subcadenas en el paso de candidaturas y en la tabla de `silver`, y un test global pasaría sin tocar esta sección.
- `.agents/data-sources.md` y `.agents/data-model.md` no se tocan: el primero describe la fuente (formato, rarezas, licencia), el segundo ya describe la identidad de `party` desde la 13. `ingestor/AGENTS.md` tampoco: sus bullets del adaptador y del loader siguen siendo ciertos.

## Comprobación real (evidencia, no acceptance)

Desde `ingestor/` contra el Postgres local, tras implementar y con los tests verdes:

1. Conteos pre: `poll`, `poll_result`, `party` (SQL de conteos de la 13).
2. `uv run ingestor ingest-polls --force` sobre el snapshot local; registrar salida, exit code y avisos (no se espera ningún `unknown party label` de las quince etiquetas; sí puede repetirse `unknown party column: FA`, que es de la fuente).
3. Conteos post: `poll`/`poll_result` idénticos y `party` sin altas nuevas.
4. Consulta de encaje: para las quince marcas, que cada `poll_result` apunte a la misma fila que usa `party_election` (o a la única fila del slug cuando no haya candidatura).

```sql
SELECT p.slug, count(DISTINCT pr.party_id), count(DISTINCT pe.party_id)
FROM silver.party p
LEFT JOIN silver.poll_result pr ON pr.party_id = p.id
LEFT JOIN silver.party_election pe ON pe.party_id = p.id
GROUP BY p.id ORDER BY p.slug;
```

La evidencia se registra en `progress/impl_party_polls.md`. Si la recarga destapara un rótulo sin ficha que deba fusionarse: alias en `data/party_catalog.toml` + recarga del snapshot (el diff del catálogo es el registro).

## Alternativas descartadas

1. **Que el adaptador emita siempre el rótulo crudo y resuelva solo el loader**: contradice el reparto de la feature 8 (las reglas de la fuente viven en el adaptador) y rompe el contrato de `PollRow.results` (claves = slug de `silver.party`), del que dependen los fixtures y el cotejo de la feature 11.
2. **Catálogo cargado en el import del adaptador** (constante de módulo): efecto secundario al importar (lectura de disco si el paquete está roto) y catálogo no inyectable en tests; el parámetro opcional mantiene el módulo puro y testeable.
3. **Resolver con el catálogo dentro del adaptador y crear filas allí**: el adaptador no toca base de datos (contrato de la feature 8); la creación de filas es del loader con el resolver compartido.
4. **Que el loader conserve `_PARTY_NAMES` como fuente de nombres y solo consulte el resolver para lo desconocido**: dos fuentes de verdad para la misma identidad —el fallo que esta feature corrige— y nombres divergentes del catálogo.
5. **Reimplementar en el loader la precedencia del resolver** (`lookup` → nombre → alta) en vez de usar `PartyResolver`: duplicaría la lógica de la 12; la identidad se resuelve en un solo sitio.
6. **Pasar el catálogo a `load_polls` como parámetro**: la 13 ya establece que el loader carga el catálogo del paquete internamente; el catálogo es configuración versionada, siempre presente, y los tests ejercitan el real (mismo criterio que la 13).
7. **Dejar de emitir claves y guardar el rótulo en `poll_result`** (columna nueva): cambio de esquema innecesario; la identidad es `party_id`, no el literal de la fuente.

## Riesgos y notas

- **Dependencia del invariante `lookup(<slug>) == ficha`**: fijada por el test de las quince; un fallo se corrige con alias en el catálogo (12), no con código.
- **`FA` como rótulo crudo en los tests**: hoy no está en el catálogo (fuera del alcance de curación de la 12). Si una curación posterior le diera ficha, `test_unknown_column_warns_and_kept` (catálogo inyectado, sin ficha) sigue siendo válido y en `test_unknown_label_creates_party_with_warning` habría que cambiar la etiqueta de prueba: es la señal, no un fallo.
- **Nombres de las fichas fuera del test**: las aserciones comparan contra `Catalog.lookup(...).name`, nunca contra literales como «Partido Popular»; el literal lo fija la extracción de la 12 y no debe repetirse aquí.
- **La feature 11 no se rompe**: los conteos y el cotejo del snapshot comparan claves (slugs), que no cambian para las quince etiquetas.
- **Resto del sistema** (Senado, autonómicas, más años de sondeos): comparten catálogo y resolver sin cambios; el adaptador resuelve cualquier rótulo con ficha, no solo los quince.
