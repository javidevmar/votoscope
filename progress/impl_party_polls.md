# Implementación — `party_polls` (feature 14, iniciativa `party-norm`)

- **Rama:** `feature/party-polls` (piso 3 del stack, sobre `feature/party-reload`).
- **Estado:** implementada; `./init.sh` verde; cambios en el working tree (sin commitear).
- **Tasks:** T1–T8 de [`specs/014_party_polls/tasks.md`](../specs/014_party_polls/tasks.md) marcadas `[x]`, en orden (TDD: test rojo → implementación).
- **Alcance respetado:** adaptador y loader de sondeos, los tres ficheros de test, `docs/ingestor/ingesta.md` (paso 6 de «Comportamiento de `ingest-polls`») y este informe. Sin tocar `models.py`, ERD ni migraciones (sin cambio de esquema); sin dependencias nuevas; sin CLI; catálogo sin cambios.

## Ficheros

| Acción | Archivo |
| --- | --- |
| modificado | `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py` — `parse_polls(wikitext, catalog=None)`, `_Column_plan`/`_read_table` resuelven con `Catalog.lookup`; borradas `PartyColumn`/`PARTY_COLUMNS`; docstrings del módulo y de `_Plan` |
| modificado | `ingestor/src/ingestor/polls/loaders/polls.py` — `_resolve_parties` por `PartyResolver`/`load_catalog`; `party_ids[key]` directo; borrados `_PARTY_NAMES`/`_party_slug`; docstring del contrato |
| modificado | `ingestor/tests/test_wikipedia_polls.py` — `test_party_labels_resolve_through_catalog`, `test_parse_resolves_label_outside_mapping`, `test_mapping_table_removed`; `test_unknown_column_warns_and_kept` con catálogo de `tmp_path`; pureza con `ingestor.parties` |
| modificado | `ingestor/tests/test_polls_load.py` — nombres de `pp`/`psoe` contrastados con `load_catalog().lookup(...).name` |
| creado | `ingestor/tests/test_party_polls.py` — 4 tests (loader por catálogo, sin mapeo local, coincidencia sondeos↔elecciones, documentos) |
| modificado | `docs/ingestor/ingesta.md` — paso 6 de «Comportamiento de `ingest-polls`» |
| creado | `progress/impl_party_polls.md` — este informe |

## TDD y tests

- T1: tests del adaptador en rojo (`4 failed`: `parse_polls` sin `catalog`, `PARTY_COLUMNS`/`PartyColumn` aún presentes, imports de `ingestor` sin `ingestor.parties`).
- T2: adaptador resuelto por `Catalog` → `27 passed` en `test_wikipedia_polls.py` (incluye los casos ya verdes del fixture `synthetic_columns.wikitext`: las claves `vox`/`pp`/`salf`/`alianca-cat`/`adelante-andalucia`/`FA` no cambian).
- T3: tests del loader en rojo (el loader aún importaba `PARTY_COLUMNS`: error de importación); `test_loader_resolves_catalog_only_label` habría fallado además por el aviso de `C's` y el slug `c-s`.
- T4: `_resolve_parties` con `PartyResolver` → `55 passed` en los tres ficheros afectados.
- T5: test de contrato `test_poll_and_election_share_party_row` (verde antes y después de T2/T4, como fija el diseño); segunda carga con revisión mayor sin altas de `party`.
- T6: `test_docs_ingesta_polls_mapping` en rojo (`parties.py` ausente de la sección) → documento actualizado → verde.
- T7: recarga real (abajo).
- T8: `./init.sh` verde: ruff check, ruff format, **199 tests** (193 previos + 6 nuevos), `alembic check` sin drift.

## Recarga real (T7)

Entorno: Postgres 18 local `1poller-db-1` (host 5434), snapshot local `data/raw/polls/wikipedia-en/2026-general/` con tres revisiones (`1380713440`, `1380777984`, `1380859635`).

### Conteos pre

```sql
SELECT 'party', count(*) FROM silver.party
UNION ALL SELECT 'poll', count(*) FROM silver.poll
UNION ALL SELECT 'poll_result', count(*) FROM silver.poll_result;
```

| Tabla | Filas |
| --- | ---: |
| `party` | 521 |
| `poll` | 575 |
| `poll_result` | 6.125 |

### Recarga

Comando, desde `ingestor/`:

```sh
uv run ingestor ingest-polls --force
```

- **Exit code: 0.**
- **3/3 snapshots `processed`** (`1380713440`, `1380777984`, `1380859635`; 575 sondeos cada uno). `silver` queda con la revisión última (`1380859635`).
- **Avisos del resolver: 0 `unknown party label`** (ninguna de las quince etiquetas; tampoco la columna `FA`, que sigue sin filas de datos).
- **Avisos del adaptador (deriva de la fuente):** `unknown party column: FA` ×3 (una por snapshot) y `unknown party column: FV` ×1 (columna sin filas de datos: no llega al loader y no crea fila de `party`). Además, `unparseable turnout: 66–67` ×3 (formato de la fuente, ya conocido). Ninguna aborta la carga.

### Conteos post

| Tabla | Filas |
| --- | ---: |
| `party` | 521 |
| `poll` | 575 |
| `poll_result` | 6.125 |

Idénticos a los pre: **ninguna alta ni duplicado de `party`** (la fila `fa` es la 301 ya existente).

### Consulta de encaje (quince marcas)

```sql
SELECT p.slug, p.name, count(DISTINCT pr.party_id) AS poll_party_ids,
       count(DISTINCT pe.party_id) AS election_party_ids
FROM silver.party p
LEFT JOIN silver.poll_result pr ON pr.party_id = p.id
LEFT JOIN silver.party_election pe ON pe.party_id = p.id
WHERE p.slug IN ('pp','psoe','vox','sumar','erc','jxcat-junts','eh-bildu',
                 'eaj-pnv','bng','cca','u-p-n','adelante-andalucia',
                 'podemos','salf','alianca-cat')
GROUP BY p.id ORDER BY p.slug;
```

| `slug` | `name` (ficha) | `poll_result` | `party_election` |
| --- | --- | ---: | ---: |
| `adelante-andalucia` | ADELANTE ANDALUCÍA | 1 | 1 |
| `alianca-cat` | Aliança Catalana | 1 | 0 (sin `03`) |
| `bng` | BNG | 1 | 1 |
| `cca` | CCa | 1 | 1 |
| `eaj-pnv` | EAJ-PNV | 1 | 1 |
| `eh-bildu` | EH Bildu | 1 | 1 |
| `erc` | ERC | 1 | 1 |
| `jxcat-junts` | JxCAT - JUNTS | 1 | 1 |
| `podemos` | PODEMOS | 1 | 1 |
| `pp` | PP | 1 | 1 |
| `psoe` | PSOE | 1 | 1 |
| `salf` | Se Acabó La Fiesta | 1 | 0 (sin `03`) |
| `sumar` | SUMAR | 1 | 1 |
| `u-p-n` | U.P.N. | 1 | 1 |
| `vox` | VOX | 1 | 1 |

Cada marca con candidatura apunta a **una sola fila** de `party` tanto en `poll_result` como en `party_election` (1/1); las dos marcas solo-sondeos (`salf`, `alianca-cat`) tienen una única fila con resultados y sin candidatura. Sin altas ni grupos duplicados.

## Trazabilidad

| Requirement | Test |
| --- | --- |
| R1 — el adaptador resuelve rótulos con `load_catalog()`/`Catalog.lookup` | `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog`, `::test_parse_resolves_label_outside_mapping` |
| R2 — rótulo con ficha → `slug` de la ficha como clave | `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog`, `::test_parse_resolves_label_outside_mapping`, `::test_synthetic_columns_mapping` |
| R3 — rótulo sin ficha → clave = rótulo crudo | `test_wikipedia_polls.py::test_unknown_column_warns_and_kept` |
| R4 — warning `unknown party column: <rótulo>` y la carga sigue | `test_wikipedia_polls.py::test_unknown_column_warns_and_kept` |
| R5 — las quince etiquetas → sus slugs y `lookup(<slug>)` = su ficha | `test_wikipedia_polls.py::test_party_labels_resolve_through_catalog` |
| R6 — sin `PARTY_COLUMNS` ni `PartyColumn` | `test_wikipedia_polls.py::test_mapping_table_removed` |
| R7 — solo stdlib + `ingestor.*` (con `ingestor.parties`), sin red ni BD | `test_wikipedia_polls.py::test_module_is_stdlib_only_and_pure` |
| R8 — el loader resuelve cada clave con `PartyResolver` | `test_party_polls.py::test_loader_resolves_catalog_only_label`, `test_polls_load.py::test_cli_registers_and_loads` |
| R9 — sin `_PARTY_NAMES` ni `_party_slug` en el loader | `test_party_polls.py::test_loader_has_no_local_party_mapping` |
| R10 — alta sin ficha con warning y `name` literal | `test_polls_load.py::test_unknown_label_creates_party_with_warning` |
| R11 — misma marca = misma fila en `poll_result` y `party_election` | `test_party_polls.py::test_poll_and_election_share_party_row` (+ consulta de encaje de T7) |
| R12 — recarga sin duplicar `party` | `test_party_polls.py::test_poll_and_election_share_party_row` (segunda carga), `test_polls_load.py::test_existing_party_and_pollster_reused`, `::test_unknown_label_creates_party_with_warning` |
| R13 — `ingesta.md` describe `parties.py` + `party_catalog.toml` en la sección de sondeos | `test_party_polls.py::test_docs_ingesta_polls_mapping` |
| R14 — sin «slugs del mapeo» en el documento | `test_party_polls.py::test_docs_ingesta_polls_mapping` |
| R15 — cobertura en los tres ficheros, sin red, adaptador sin BD | `test_wikipedia_polls.py` (sin `db`), `test_polls_load.py`, `test_party_polls.py` |

## Decisiones

- **Sin cambios de catálogo:** las quince etiquetas resolvieron contra las fichas de la 12; la recarga no destapó ninguna marca sin ficha que fusionar (0 `unknown party label`).
- **`FV`:** columna de la fuente sin ficha y sin filas de datos; el adaptador la avisa y no llega al loader, así que no crea `party` (mismo camino que `FA`).
- **Tests de contrato:** `test_poll_and_election_share_party_row` nace verde (ambas rutas ya coincidían en `bng`); su valor es impedir que la sustitución rompa la coincidencia. El test que nace rojo es `test_loader_resolves_catalog_only_label`.
- **Sin recarga de candidaturas:** la feature no cambia `party_election`; el encaje se comprueba con el `silver` de la 13.
