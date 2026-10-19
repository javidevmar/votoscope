# Implementación — `party_catalog` (feature 12, iniciativa `party-norm`)

- **Rama:** `feature/party-catalog` (piso 1 del stack).
- **Estado:** implementada, `./init.sh` verde (183 tests: 140 previos + 43 nuevos en `ingestor/tests/test_parties.py`). Pendiente `reviewer` y OK del usuario; sin commitear.
- **Tasks:** T1–T13 de [`specs/012_party_catalog/tasks.md`](../specs/012_party_catalog/tasks.md) marcadas `[x]`, en orden (TDD: test rojo → implementación).
- **Alcance respetado:** solo `src/ingestor/{parties.py,data/party_catalog.toml}`, `tests/test_parties.py`, `tests/fixtures/party_catalog/brands_2023.txt` y los imports de `slugify` en `elections/loaders/election.py` y `polls/loaders/polls.py`. Sin tocar `.agents/`, `docs/`, `models.py`, migraciones ni CLI; sin integrar los loaders con el resolver (features 13/14).

## Ficheros

| Acción | Archivo |
| --- | --- |
| creado | `ingestor/src/ingestor/data/party_catalog.toml` — 79 fichas, literales de la extracción (5 con alias) |
| creado | `ingestor/src/ingestor/parties.py` — `normalize`, `slugify`, `PartyEntry`, `Catalog`, `load_catalog`, `PartyResolver` |
| creado | `ingestor/tests/test_parties.py` — 43 tests (sin red ni BD) |
| creado | `ingestor/tests/fixtures/party_catalog/brands_2023.txt` — 59 grafías del 23-jul-2023 (volcado literal) |
| modificado | `ingestor/src/ingestor/elections/loaders/election.py` — `slugify` importada de `parties.py`; sin copia local |
| modificado | `ingestor/src/ingestor/polls/loaders/polls.py` — `slugify` importada de `parties.py` |

## Extracción usada

Contra el `silver` local (`1poller-db-1`, puerto 5434) con los 13 procesos del Congreso:

```
party=549  party_election=2106  election=13  poll=575  poll_result=6125
```

**1. Volcado del alcance 2023** (origen de `brands_2023.txt`, SQL de `design.md` §Curación):

```sql
SELECT DISTINCT p.name
FROM silver.party p
JOIN silver.party_election pe ON pe.party_id = p.id
JOIN silver.election e ON e.id = pe.election_id
WHERE e.type = 'congress' AND e.date = DATE '2023-07-23'
ORDER BY 1;
```

Salida (59 líneas; copiada tal cual, una grafía por línea, a `ingestor/tests/fixtures/party_catalog/brands_2023.txt`):

```
3e · ADELANTE ANDALUCÍA · AHORA CANARIAS-PCPC · ALM · ASTURIAS EXISTE EV · B.N.G. · BQEX ·
CCa · CCD · CJ · CpM · CUP-PR · EAJ-PNV · EH Bildu · ERC · ESCAÑOS EN BLANCO · ESPAÑA VACIADA ·
EVB · EVC · EV-PCAS-TC · EXISTE · FE de las JONS · F.I.A. · FO · FUERZA CÍVICA · GBAI · GITV ·
JM+ · JxCAT - JUNTS · JxG · LB · NC-bc · PACMA · PAR · PARTIDO AUTÓNOMOS · PCTE · PDeCAT-E-CiU ·
PH · POR MI REGIÓN · PP · PREPAL · PSOE · PUEDE · PUM+J · +RDS+ · RECORTES CERO · Somos Cc ·
SUMAR · SY · Ud.Ca · UNIDOS SI · U.P.L. · U.P.N. · VB · VOX · VP · XAV · XH · Zsi
```

**2. Volcado completo para redactar las fichas** (nombres y siglas literales; no se commitea):

```sql
SELECT p.slug, p.name,
       array_to_string(array_agg(DISTINCT pe.short_name ORDER BY pe.short_name), ', ')
FROM silver.party p JOIN silver.party_election pe ON pe.party_id = p.id
GROUP BY p.id ORDER BY p.slug;
```

547 filas (las 549 de `party` menos 2 huérfanas sin candidaturas: `salf` y `alianca-cat`, creadas por `ingest-polls`). De ahí salen los `name` literales de las fichas de marca y los alias (`UNIDOS PODEMOS` es `short_name` de la cabecera `podemos-iu-equo` del 26-jun-2016). Las cifras del diagnóstico se confirman: `p-p`/`pp`, `c-s`/`cs`, `i-u`/`iu`, `p-c-p-e`/`pcpe`, `u-p-l`/`upl`, `f-i-a`/`fia`, `d-n`/`dn`, `a-u-n`/`aun`… y el 2023 está en la fila punteada de BNG, UPL y FIA.

**Comprobación de fidelidad** (ad-hoc, no commiteada): los 1668 literales distintos de `name`/`short_name` de `party`/`party_election` (`SELECT DISTINCT p.name … UNION SELECT DISTINCT pe.short_name/pe.name …`) contienen todos los `name` del catálogo y el alias `UNIDOS PODEMOS`; los únicos valores no literales son los 3 rótulos de sondeos que fija R10 (`Junts`, `PNV`, `Adelante Andalucía (2021)`) y la grafía `Unidas Podemos` que exige R14.

## Decisiones de curación (revisables en el diff)

Criterio de la iniciativa (design.md §Decisión): continuidad de la **marca electoral**; fusionar solo grafías de la misma marca (por normalización o alias explícito); **sin fuzzy**; **ante la duda, no fusionar**.

1. **Parejas punteadas (R13): se fusionan por normalización, sin alias.** `B.N.G.`/`BNG`, `P.P.`/`PP`, `P.S.O.E.`/`PSOE`, `C's`/`Cs`, `I.U.`/`IU`, `P.C.P.E.`/`PCPE`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `D.N.`/`DN`, `A.u.N.`/`AUN`: la grafía limpia es la canónica (`bng`, `pp`, `psoe`, `cs`, `iu`, `pcpe`, `upl`, `fia`, `dn`, `aun`) y la punteada coincide por `normalize`, así que no lleva alias (R6 lo prohibiría: sería redundante con su propio nombre). Efecto esperado en la recarga (feature 13): las filas 2023 `B.N.G.`, `U.P.L.` y `F.I.A.` se fusionan con sus grafías limpias.
2. **Alias solo donde la normalización no coincide** (5 fichas):
   - `jxcat-junts` ← `"Junts"` (rótulo de sondeos, R10; el literal del 03 es `JxCAT - JUNTS`).
   - `eaj-pnv` ← `"PNV"` (rótulo de sondeos, R10; el literal es `EAJ-PNV`).
   - `adelante-andalucia` ← `"Adelante Andalucía (2021)"` (rótulo de sondeos, R10; el literal del 03 no lleva año).
   - `podemos-iu-equo` ← `"UNIDOS PODEMOS"` (sigla literal de la cabecera del 26-jun-2016 en `silver`).
   - `podemos-iu` ← `"Unidas Podemos"` (R14 exige esa grafía; `silver` solo tiene `UNIDOS PODEMOS` del 2016). Se asigna a la cabecera **del 2019** (`PODEMOS-IU-`, nombre literal truncado en el 03), no a la del 2016, para no fusionar 2016 y 2019: R15 exige tres slugs distintos para `Podemos` / `Unidas Podemos` / `Sumar` y quedan `podemos`, `podemos-iu`, `sumar`.
3. **Familias del diagnóstico (R14): fichas propias, sin fusionar entre sí.** Verdes (`lv`, `lve`, `lv-gv`, `verdes`), falange (`fe-de-las-j`, `fe-de-las-jons`, `fe-jons`), `na`/`na-bai`, `erc`/`esquerra`/`erc-catsi`, familia Podemos (`podemos`, `podemos-iu`, `podemos-iu-equo`). Son grafías de marcas distintas, no variantes de puntuación; fusionarlas es una decisión posterior (alias + reingesta) y el diff del catálogo es el registro.
4. **Sondeos sin 03 (`salf`, `alianca-cat`):** `name` con el literal del adaptador (R11): `Se Acabó La Fiesta` y `Aliança Catalana` — los mismos que `ingest-polls` ya escribió en los huérfanos de `silver`. Sin alias: el rótulo `SALF` coincide con la clave del slug y `Aliança.cat` normaliza a `ALIANCACAT`, la clave del slug `alianca-cat` (un alias sería redundante).
5. **Marcas del 2023 (R12):** 59 grafías → 56 fichas nuevas + 3 cubiertas por normalización (B.N.G.→`bng`, F.I.A.→`fia`, U.P.L.→`upl`). Todas con `name` literal del volcado.
6. **Resto del alcance:** los micro-partidos de otros procesos no llevan ficha (caen por coincidencia por nombre, R19); fichas de más no estorban, pero no se inventan marcas fuera del alcance.

## Trazabilidad R1–R28 ↔ test

Todos en `ingestor/tests/test_parties.py` (sin red ni base de datos; `ML = load_catalog`/`Resolver` con TOML de `tmp_path` y filas `Party` transitorias).

| R | Test |
| --- | --- |
| R1 | `test_normalize_matrix` (puntuación, `ç`/`ñ`, tildes, espacios, claves vacías) |
| R2 | `test_catalog_loads_toml` (varias fichas, alias opcional), `test_catalog_loads_bundled` (ruta por defecto) |
| R3 | `test_catalog_lookup_by_name_and_alias` (nombre, alias, coincidencia por normalización), `test_catalog_integrity` (invariante `lookup(<slug>) is ficha` para todas las fichas) |
| R4 | `test_catalog_lookup_unknown_returns_none` |
| R5 | `test_load_catalog_rejects_duplicate_key` + `test_catalog_integrity` (el catálogo real carga sin conflicto) |
| R6 | `test_load_catalog_rejects_redundant_alias` + `test_catalog_integrity` (sin alias redundante en el real) |
| R7 | `test_load_catalog_rejects_key_without_alnum` (nombre y alias) |
| R8 | `test_load_catalog_rejects_missing_file_and_bad_toml` (inexistente, TOML roto, tabla repetida, sin `[parties]`) |
| R9 | `test_load_catalog_rejects_entry_without_name` |
| R10 | `test_catalog_poll_labels` (las 15 etiquetas → sus slugs) |
| R11 | `test_catalog_poll_labels` (nombres de `salf`/`alianca-cat`) |
| R12 | `test_catalog_covers_2023_brands` (fixture `brands_2023.txt`, ≥50 líneas, todas resuelven) |
| R13 | `test_catalog_punctuation_pairs` (10 parejas → misma ficha) |
| R14 | `test_catalog_families_resolve` (14 grafías) |
| R15 | `test_catalog_coalitions_do_not_merge` (3 slugs distintos) |
| R16 | `test_resolve_no_fuzzy_matching` (`PPX` → `ppx`, no `pp`) |
| R17 | `test_resolve_uses_catalog_slug` (ficha → fila por slug o creación con `name` de la ficha) |
| R18 | `test_resolve_catalog_creation_without_warning` (`caplog` vacío) |
| R19 | `test_resolve_matches_existing_name` (no crea fila) |
| R20 | `test_resolve_tie_break_slug_wins` |
| R21 | `test_resolve_tie_break_lowest_id` |
| R22 | `test_resolve_creates_with_warning` (nombre literal, slug recortado a 60) |
| R23 | `test_resolve_collision_suffix` (`-code`, `-2`, recorte que reserva espacio al sufijo) |
| R24 | `test_resolve_creates_with_warning` (`unknown party label: <etiqueta> -> <slug>`), `test_resolve_is_idempotent` (un solo warning) |
| R25 | `test_resolve_is_idempotent` (dos llamadas y dos etiquetas de la misma ficha → una fila) |
| R26 | `test_slugify_single_source` (`election.slugify is polls.slugify is parties.slugify` + casos) |
| R27 | `test_module_has_no_new_dependencies` (imports por `ast` ⊆ stdlib + `ingestor`; `pyproject.toml` con las cuatro dependencias aprobadas) |
| R28 | `test_catalog_integrity` (invariante por slug), `test_catalog_covers_2023_brands` (fixture); el módulo de tests no importa red ni sesiones de BD |

## Notas

- El wheel (`uv build` de comprobación, en un directorio temporal) incluye `ingestor/data/party_catalog.toml`: `CATALOG_PATH` resuelve también fuera de la instalación editable.
- `ingestor/tests/test_rules.py` no se toca: importa `slugify` de `election`, que la re-exporta y su comportamiento no cambia.
- Sin cambios de modelo (la regla de oro no aplica): `docs/db/schema.drawio`, `models.py` y Alembic intactos; `alembic check` sin drift.
- Documentación de comportamiento (`docs/ingestor/ingesta.md`, `ingestor/AGENTS.md`, `.agents/data-model.md`): se actualiza en la feature 13, que es la que integra el resolver (design.md §Documentación).
- Warnings: solo `unknown party label: <etiqueta> -> <slug>` en el alta sin ficha; sin logs INFO/DEBUG (convención del repo).

## Auditoría de grafías anteriores (leader, tras el review)

Simulación de la recarga de los 13 procesos (cabeceras reales del `03`) contra el catálogo y el `silver` actual, sin escribir:

- **921 etiquetas de cabecera → 0 altas** (ningún `unknown party label`): todas las grafías anteriores resuelven por normalización (`B.N.G.`→`bng`, `P.P.`→`pp`, `P.S.O.E.`→`psoe`, `C's`→`cs`, `I.U.`→`iu`, `U.P.L.`→`upl`, `F.I.A.`→`fia`, `D.N.`→`dn`, `A.u.N.`→`aun`, `P.C.P.E.`→`pcpe`…). Los alias solo cubren grafías que no coinciden por normalización (Junts, PNV, Adelante Andalucía (2021), Unidas Podemos, UNIDOS PODEMOS); un alias redundante lo rechaza `load_catalog` (R6).
- **0 grupos duplicados por nombre normalizado** tras la recarga; las 7 marcas del acceptance (BNG/UPL/FIA/Cs/PP/PSOE/IU) quedan en una fila cada una.
- **28 filas legadas** quedan huérfanas y las borrará la limpieza de la 13 (`f-i-a`, `u-p-l`, `b-n-g`, `c-s`, `i-u`, `p-p`, `p-s-o-e`, `d-n`, `a-u-n`, `p-c-p-e`, `fe-i`, `e-u`, `fe-a`, `uni-d-a`, `lv-cm`, `l-i-lit-ci`, `lv-e`, `c-d-s`, `e-v-a-v`, `f-a`, `i-m-c`, `li-litci`, `p-c`, `p-o-s-i`, `p-r-gu`, `u-r-c-l`, `p-r-c`, `i-fem`); sus grafías siguen en `party_election.short_name`.
- Fuera del alcance de curación (no se tocan): la familia de Coalición Canaria sigue partida por siglas que no son puntuación (`CC` 1993–2004, `CC-PNC` 2008, `CC-NC-PNC` 2011, `CCa-PNC` 2015–2019, `CCa-PNC-NC` 2019, `CCa` 2023). `JXC` es «Juntos por Canarias» (marca distinta; correcto no fusionarla con JxCAT-Junts). Candidato a una curación posterior si se quiere la serie canaria continua.
- Limitación pre-existente de la normalización (no la introduce esta feature): `+MAS+` (Muerte al Sistema) y `MAS` (Movimiento Aragonés Social) comparten fila; `NA` (Nación Andaluza) y `NA+` (Navarra Suma) también. Las fusionó el slug del loader antiguo y los alias no pueden separarlas (la normalización colapsa `+`).
