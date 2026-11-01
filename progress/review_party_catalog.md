# Review — feature 12 `party_catalog` (iniciativa `party-norm`)

**Veredicto:** APPROVED

Rama `feature/party-catalog` (piso 1 del stack), cambios en el working tree sin commitear (correcto: el commit llega tras el OK del usuario). Revision contra `specs/012_party_catalog/`, `.agents/`, `CHECKPOINTS.md` y el `silver` local.

Verificaciones independientes ejecutadas por el reviewer (además de la suite):

- `./init.sh` **verde** de principio a fin: `uv sync`, `ruff check`, `ruff format --check`, `pytest` **183 passed** (140 previos + 43 nuevos), `alembic check` sin drift, exit 0.
- `diff` de `ingestor/tests/fixtures/party_catalog/brands_2023.txt` contra el volcado real de `silver` (query de `design.md` §Curación sobre los 13 procesos): **coincidencia exacta, 59/59 líneas** (`party`=549, `party_election`=2106, `election`=13).
- Fidelidad de literales del catálogo contra `silver`: de los 79 fichas (157 valores name+aliases), los únicos no literales son exactamente las 4 excepciones documentadas en `progress/impl_party_catalog.md`: `Adelante Andalucía (2021)`, `PNV`, `Junts` (rótulos de `PARTY_COLUMNS`, R10) y `Unidas Podemos` (exigido por R14/R15).
- Cross-check independiente de las 15 etiquetas contra el `PARTY_COLUMNS` **real** de `polls/adapters/wikipedia_polls.py` (no la copia hardcodeada del test): 0 mismatches; `salf`→`Se Acabó La Fiesta`, `alianca-cat`→`Aliança Catalana`.
- `grep "def slugify"` en `ingestor/src`: definición única en `parties.py:35`.
- Wheel (`uv build`): `ingestor/data/party_catalog.toml` incluido en el paquete.
- Sin `print()`/TODO en los ficheros nuevos; `pyproject.toml` sin tocar (4 dependencias aprobadas).

## Trazabilidad requirements ↔ tests

Todos en `ingestor/tests/test_parties.py` (43 tests, sin red ni BD; catálogos de `tmp_path` y filas `Party` transitorias).

- R1: [x] `test_normalize_matrix` (puntuación `.`/`'`/`-`, `ç` vía `Aliança.cat`/`Ç`, tildes, espacios, claves vacías)
- R2: [x] `test_catalog_loads_toml` (alias opcional), `test_catalog_loads_bundled` (ruta por defecto)
- R3: [x] `test_catalog_lookup_by_name_and_alias`, `test_catalog_integrity` (invariante `lookup(<slug>) is entry` para las 79 fichas)
- R4: [x] `test_catalog_lookup_unknown_returns_none`
- R5: [x] `test_load_catalog_rejects_duplicate_key` (mensaje con la clave en conflicto)
- R6: [x] `test_load_catalog_rejects_redundant_alias`
- R7: [x] `test_load_catalog_rejects_key_without_alnum` (name y alias)
- R8: [x] `test_load_catalog_rejects_missing_file_and_bad_toml` (inexistente, TOML roto, tabla repetida, sin `[parties]`; mensaje con la ruta)
- R9: [x] `test_load_catalog_rejects_entry_without_name` (mensaje con el slug)
- R10: [x] `test_catalog_poll_labels` (15 etiquetas → slugs) + cross-check del reviewer contra el `PARTY_COLUMNS` real
- R11: [x] `test_catalog_poll_labels` (nombres `Se Acabó La Fiesta` / `Aliança Catalana`)
- R12: [x] `test_catalog_covers_2023_brands` (fixture ≥50 líneas, todas resuelven; fixture = volcado real, verificado contra `silver`)
- R13: [x] `test_catalog_punctuation_pairs` (las 10 parejas → misma ficha)
- R14: [x] `test_catalog_families_resolve` (14 grafías de familias)
- R15: [x] `test_catalog_coalitions_do_not_merge` (3 slugs distintos)
- R16: [x] `test_resolve_no_fuzzy_matching` (`PPX` → `ppx`, no `pp`)
- R17: [x] `test_resolve_uses_catalog_slug` (fila por slug o creación con `name` de la ficha)
- R18: [x] `test_resolve_catalog_creation_without_warning` (`caplog.records == []`)
- R19: [x] `test_resolve_matches_existing_name`
- R20: [x] `test_resolve_tie_break_slug_wins`
- R21: [x] `test_resolve_tie_break_lowest_id`
- R22: [x] `test_resolve_creates_with_warning` (nombre literal; slug = `slugify(label)[:60]`)
- R23: [x] `test_resolve_collision_suffix` (`-code`, `-2`, y recorte que reserva hueco al sufijo, ≤60)
- R24: [x] `test_resolve_creates_with_warning` + `test_resolve_is_idempotent` (forma `unknown party label: <etiqueta> -> <slug>`)
- R25: [x] `test_resolve_is_idempotent` (dos llamadas y dos etiquetas de la misma ficha → una fila, un warning)
- R26: [x] `test_slugify_single_source` (`election.slugify is polls.slugify is parties.slugify`; grep confirma definición única en `parties.py:35`)
- R27: [x] `test_module_has_no_new_dependencies` (imports por `ast` ⊆ stdlib+`ingestor`, `tomllib` incluido; `pyproject.toml` con las 4 dependencias aprobadas, sin diff)
- R28: [x] tests en `ingestor/tests/test_parties.py` sin red/BD (imports verificados); invariante `lookup(<slug>)` en `test_catalog_integrity`; fixture usada en R12

## Tasks completas

`specs/012_party_catalog/tasks.md`: T1–T13 todas `[x]`, sin justificaciones pendientes.

- T1–T13: [x]

## Checkpoints

- C1: [x] piezas base y 4 agentes presentes (`init.sh` §2 los verifica); `./init.sh` exit 0.
- C2: [x] una sola `in_progress` (12); 183 tests verdes incluidas las features previas; `progress/current.md` describe la sesión activa.
- C3: [x] sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican; `alembic check` sin drift); sin DDL a mano; arquitectura respetada (módulo de soporte stdlib-only, resolver puro sin sesiones, capa ingestador intacta); sin dependencias nuevas; logging por `getLogger(__name__)` con warning perezoso y formato del diseño; sin `print()` ni TODOs.
- C4: [x] `pytest`/`ruff check`/`ruff format`/`alembic check` verdes en local. CI ([ ] no verificable aún): `ingestor.yml` corre en push/PR y la rama no está commiteada/pusheada por diseño (commits tras el OK del usuario); el equivalente local está verde.
- C5: [x] sin archivos temporales ni basura (solo los ficheros previstos, incl. `data/party_catalog.toml` correctamente incluido en el wheel); feature 12 en `in_progress` (estado correcto antes del OK del usuario). [ ] `progress/history.md` y los commits atómicos quedan pendientes por diseño del flujo (se hacen al cerrar sesión, tras el OK).
- C6: [x] carpeta con los 3 archivos; EARS con los patrones del proceso (observación menor no bloqueante: R3 y R23 contienen dos cláusulas `DEBE` cada uno, ambas verificadas por tests; el spec ya pasó la puerta humana); tasks `[x]`; R1–R28 cubiertos con test concreto.

## Cambios requeridos

Ninguno. Alcance respetado: sin tocar loaders (13/14), sin tocar `docs/`/`AGENTS.md`/`.agents/data-model.md` (diferido a la 13 según `design.md` §Documentación), sin modelo/CLI.
