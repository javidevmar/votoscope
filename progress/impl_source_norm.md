# Implementación — 18 `source_norm`

- Rama: `feature/source-norm` (desde `main`, con la 14 `party_polls` ya mergeada).
- Spec: [`specs/018_source_norm/`](../specs/018_source_norm/).
- Estado: T1–T15 completadas (`./init.sh` verde); feature **no** marcada `done` (leader/reviewer).

## Qué se implementó

- `Signature` + `parse_signature(source)` en
  `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py`: paréntesis final →
  reestimador; primera barra del resto → encuestadora/medio; sin separadores →
  solo encuestadora. Partes vacías → warning `signature part is empty` y nulo.
  `PollRow` gana `media`/`reestimator`; `_read_row` los rellena y `_pollster_name`
  desaparece.
- `silver.poll.media` / `silver.poll.reestimator`: `Text` nulables en
  `models.py`, migración autogenerada
  `ingestor/alembic/versions/0fa48964369e_poll_source_roles.py` (dos
  `add_column`, sin `CREATE SCHEMA`), ERD «Silver polls» y `.agents/data-model.md`.
- `load_polls` escribe `media`/`reestimator` en cada fila (sustitución total;
  recarga idempotente, sin código extra).
- Docs: `.agents/data-sources.md` (papeles del literal),
  `docs/ingestor/ingesta.md` (paso 6, fila `poll`, recarga `--force`),
  `ingestor/AGENTS.md` (bullet de `src/ingestor/polls/`).

## Literales usados (unión de `data/raw/polls/**`)

Los tres snapshots locales dan la **misma unión de 43 literales**; el inventario
del `design.md` no cambia (no hay literales nuevos ni históricos):

```
40dB/Prisa, Ateneo del Dato, Ateneo del Dato/elDiario.es, Celeste-Tel/Onda Cero,
CIS, CIS (Ateneo del Dato), CIS (Demócrata), CIS (Jaime Miquel), CIS (JM),
CIS (Logoslab), CIS (Opina 360), CIS (SocioMétrica), CIS (Sondaxe),
CIS (Target Point), Cluster17/Agenda Pública, Data10/Okdiario,
Demoscopia y Servicios/esRadio, DYM/Henneo, EM-Analytics/Electomanía, GAD3/ABC,
GAD3/Mediaset, GAD3/Vocento, GESOP/Prensa Ibérica, Hamalgama Métrica/Vozpópuli,
IMOP/El Confidencial, InvyMark/laSexta, Ipsos/La Vanguardia, KeyData/Público,
More in Common, NC Report/La Razón, ODEC/Mediaflows–UV, Opina 360/Antena 3,
Opina 360/Telecinco, PSOE, Sigma Dos/Antena 3, Sigma Dos/El Mundo,
Simple Lógica/elDiario.es, SocioMétrica/El Español, SocioMétrica/PP,
Sondaxe/La Voz de Galicia, Sumar, Target Point/El Debate, Winston/Artículo14
```

Snapshots: `1380713440`, `1380777984`, `1380859635` (575 filas cada uno).

## Evidencia operativa (T15)

Entorno: Postgres local `:5434` (`docker compose`), fecha 2026-11-01.

### Migración

```
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 9f3c2a1b7d40 -> 0fa48964369e, poll source roles

$ uv run alembic check
No new upgrade operations detected.
```

### Recarga

```
$ uv run ingestor ingest-polls --force     # exit=0
... 1380713440.wikitext: processed revision 1380713440 (575 polls)
... 1380777984.wikitext: processed revision 1380777984 (575 polls)
... 1380859635.wikitext: processed revision 1380859635 (575 polls)
```

Warnings esperados de la fuente (no de esta feature): `unknown party column: FA`,
`unknown party column: FV`, `unparseable turnout: 66–67`.

### SQL de comprobación

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE media IS NOT NULL) AS con_medio,
       count(*) FILTER (WHERE reestimator IS NOT NULL) AS con_reestimador,
       count(*) FILTER (WHERE media IS NULL AND reestimator IS NULL) AS solo_encuestadora
FROM silver.poll;
```

```
(575, 479, 54, 42)
```

Spot-check (`CIS (Target Point)`, `SocioMétrica/El Español`, `More in Common`):

```
('CIS (Target Point)', None, 'Target Point')        × 5
('More in Common', None, None)                      × 3
('SocioMétrica/El Español', 'El Español', None)     × 35
```

Estado final: `revision_id = 1380859635`, 575 filas.

## Trazabilidad

- R1 → `test_parse_signature_real_literals` (casos con barra), `test_pollster_name_extraction`, `test_real_head_first_rows`
- R2 → `test_parse_signature_real_literals` (casos CIS), `test_pollster_name_extraction`, `test_real_cis_block`
- R3 → `test_parse_signature_real_literals` (`Ateneo del Dato`, `CIS`, `More in Common`, `PSOE`, `Sumar`), `test_pollster_name_extraction`
- R4 → `test_parse_signature_combined_and_empty_parts` (`Firm/Media (X)`)
- R5 → `test_parse_signature_combined_and_empty_parts` (`Firm/`, `CIS ()`: nulo + `signature part is empty`)
- R6 → `test_parse_signature_real_literals`, `test_pollster_name_extraction`, `test_real_head_first_rows`, `test_real_cis_block`
- R7 → `test_real_head_first_rows`, `test_real_cis_block`, `test_pollster_name_extraction` (aserciones de `source` literal)
- R8 → `test_poll_source_roles_are_nullable_text`
- R9 → `test_poll_source_roles_are_nullable_text` (declaración en `models.py`) + migración `0fa48964369e` autogenerada
- R10 → `uv run alembic upgrade head` + `uv run alembic check` (paso 6 de `./init.sh`, sin drift)
- R11 → `test_silver_polls_page_has_complete_tables`
- R12 → `test_data_model_v2_describes_polls_tables`
- R13 → `test_cli_registers_and_loads`
- R14 → `test_reload_roles_is_idempotent` (+ evidencia de recarga real)
- R15 → `test_parse_signature_real_literals` (43 casos, unión del bronce)
- R16 → `test_cli_registers_and_loads`, `test_reload_roles_is_idempotent`, `test_poll_source_roles_are_nullable_text`, `test_silver_polls_page_has_complete_tables`, `test_data_model_v2_describes_polls_tables`, `test_docs_ingesta`, `test_docs_ingestor_agents`, `test_docs_data_sources_quirks`
- R17 → `test_docs_data_sources_quirks`
- R18 → `test_docs_ingesta`
- R19 → `test_docs_ingestor_agents`
- R20 → `test_parse_signature_unknown_literal` (literal no inventariado) + tabla de 43 literales reales

## Desviaciones y observaciones

- **`ingestor/tests/test_gold.py`**: `test_silver_metadata_has_no_new_aggregates`
  fija la lista de columnas de `silver.poll`; se actualiza con `media`/`reestimator`.
  No es una decisión de diseño nueva, pero el design no lo listaba y sin el cambio
  la suite no queda verde.
- **ERD**: `validate_erd.py` sobre el fichero completo reporta los 8 errores de
  ids raíz duplicados (`0`/`1`) que ya existen en `HEAD` en un drawio multi-página
  (y los warnings de PK de las vistas `gold`). La página «Silver polls» aislada
  valida con **0 errores y 0 warnings**; el test de modelo parsea el fichero y pasa.
- **Regex del paréntesis**: se usa literalmente `.+?` del design; por eso un
  literal desnudo `()` no encaja en la regla del paréntesis (no hay test ni caso
  real). `/Medio` sí deja `pollster_name` vacío y el loader aborta como hoy.
- **Sin dependencias nuevas**; sin cambios en `web/` ni en la CLI.
- No se commitea ni se marca la feature `done`: working tree pendiente de revisión.

## Prueba end-to-end con fetch real (2026-11-01, tras el review)

`fetch-polls` resolvió una revisión nueva no presente en el bronce anterior
(`1383194971`, 2026-11-01T13:22:47Z) y `ingest-polls` la cargó sin `--force`
(exit 0, `processed revision 1383194971 (583 polls)`).

- `silver.poll`: 583 filas, `revision_id = 1383194971`, 43 literales distintos.
- 486 con `media`, 54 con `reestimator`, 43 solo encuestadora.
- Ningún literal con `/` o `(` quedó sin descomponer.
- Mismos 9 reestimadores y 27 medios que el inventario; sin literales nuevos.
- Spot-check: `CIS (Target Point)` → `CIS` / NULL / `Target Point` (×5);
  `SocioMétrica/El Español` → `SocioMétrica` / `El Español` / NULL (×36);
  `More in Common` → NULL / NULL; `ODEC/Mediaflows–UV` → `Mediaflows–UV` (en dash intacto).

**Deriva de la fuente detectada (fuera del alcance de la 18).** La revisión nueva
añade dos columnas de partido (`FA`, `FV`) y 5 filas con `colspan="2"` en una celda
de partido; el lexer no expande `colspan` en filas de datos y `_read_table` las
descarta por «column count mismatch» (18 != 19), así que se perdían 5 sondeos
reales, más una fila vacía que tampoco se clasifica como separador. Lo cazan
`test_completeness_arithmetic_no_lost_rows` y `test_live_poll_brands_colored`
(partidos `fa`/`fv` fuera del catálogo). Se registra como feature 20
`poll_source_drift` (pending, sdd).

**Estado local restaurado** para cerrar la 18 contra la revisión estable
`1380859635`: snapshot nuevo movido fuera de `data/raw/polls/`, registro de
bronce borrado, `ingest-polls --force` (575 filas) y fila `fv` (sin referencias)
eliminada; `fa` se conserva porque tiene `party_election` de las generales.
