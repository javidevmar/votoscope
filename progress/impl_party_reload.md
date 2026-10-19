# Implementación — `party_reload` (feature 13, iniciativa `party-norm`)

- **Rama:** `feature/party-reload` (piso 2 del stack, sobre `feature/party-catalog`).
- **Estado:** implementada; `./init.sh` verde; cambios en el working tree (sin commitear).
- **Tasks:** T1–T8 de [`specs/013_party_reload/tasks.md`](../specs/013_party_reload/tasks.md) marcadas `[x]`, en orden (TDD: test rojo → implementación).
- **Alcance respetado:** `elections/loaders/election.py`, `tests/test_rules.py`, `tests/test_parties.py` (una aserción colgada del re-export, ver §Decisiones), `tests/test_party_reload.py`, `tests/fixtures/party_reload/`, los tres documentos y este informe. Sin tocar `models.py`, ERD ni migraciones (sin cambio de esquema); sin dependencias nuevas; sin CLI; catálogo sin cambios.

## Ficheros

| Acción | Archivo |
| --- | --- |
| modificado | `ingestor/src/ingestor/elections/loaders/election.py` — `_resolve_parties` por `PartyResolver(session.scalars(select(Party)), load_catalog())`; sin slug provisional; `slugify` fuera del módulo |
| modificado | `ingestor/tests/test_rules.py` — `slugify` importada de `ingestor.parties` |
| modificado | `ingestor/tests/test_parties.py` — `test_slugify_single_source` ya no exige el re-export de `election` |
| creado | `ingestor/tests/test_party_reload.py` — 6 tests (3 de integración + 3 de documentos) |
| creado | `ingestor/tests/fixtures/party_reload/{02200806,02201905,02202601}/` — 02/03/09/10 sintéticos (12 ficheros) |
| modificado | `.agents/data-model.md` — identidad de `party` por `parties.py` + catálogo; sin «provisional» |
| modificado | `docs/ingestor/ingesta.md` — paso 4 y fila `party` de «Qué queda en `silver`»; sin «provisional» |
| modificado | `ingestor/AGENTS.md` — `parties.py` y `party_catalog.toml` en «Ficheros» |
| creado | `progress/impl_party_reload.md` — este informe |

## TDD y tests

- T1: fixtures sintéticas validadas con `file02`/`file03`/`file09`/`file10` (2008-06-15 `B.N.G.`, 2019-05-26 `BNG`, 2026-01-01 `PARTIDO SIN FICHA`; una mesa, 300 votos, 09/10 internamente consistentes).
- T2: tests de integración en rojo antes de tocar el loader (`3 failed`: dos filas `party`, sin warning de alta).
- T3: loader delegado → `test_two_processes_one_party`, `test_unknown_head_label_warns` y `test_force_reload_preserves_facts` en verde.
- T4: verificación de estado (solo lectura) con el `silver` previo y el SQL de `design.md`: 27 grupos por puntuación, 14 filas de marcas, R7 y R10 ya en verde. Esa comprobación se documentó entonces con `test_state_*`; los tests se eliminaron después (ver §«Cambio de criterio»).
- T5–T6: recarga real y limpieza (abajo).
- T7: tests de documentos en rojo → documentos actualizados → verde.
- T8: `./init.sh` verde (189 tests: 183 previos + 6 nuevos), ruff check/format y `alembic check` sin drift.

## Recarga real

Entorno: Postgres 18 local `1poller-db-1` (host 5434), 13 procesos en `data/raw/congreso/`.

### Conteos pre (2026-10-19, antes de recargar)

```sql
SELECT 'party', count(*) FROM silver.party
UNION ALL SELECT 'party_election', count(*) FROM silver.party_election
UNION ALL SELECT 'vote', count(*) FROM silver.vote
UNION ALL SELECT 'turnout', count(*) FROM silver.turnout
UNION ALL SELECT 'poll_result', count(*) FROM silver.poll_result;
```

| Tabla | Filas |
| --- | ---: |
| `party` | 549 |
| `party_election` | 2.106 |
| `vote` | 6.047.666 |
| `turnout` | 708.023 |
| `poll_result` | 6.125 |

### Recarga (T5)

Comando, desde `ingestor/`:

```sh
uv run ingestor ingest ../data/raw/congreso --force
```

- **Exit code: 0.**
- **13/13 procesos `processed`**: `02198606`, `02198910`, `02199306`, `02199603`, `02200003`, `02200403`, `02200803`, `02201111`, `02201512`, `02201606`, `02201904`, `02201911`, `02202307` (5 ficheros cada uno).
- **Cabeceras nacionales resueltas:** 921 (suma de cabeceras distintas de cada `03`; 51–98 por proceso).
- **Avisos del resolver:** **0 `unknown party label`**. No hizo falta añadir alias ni reingestar (el bucle del spec no se activó).
- **Otros avisos:** solo las inconsistencias conocidas de los ficheros del ministerio (mesas donde la suma del `10` no cuadra con el `09`), en los años relajados del adaptador: 1986 (7 mesas, neto +563), 1989 (15, +1.605), 1993 (16, +1.179), 1996 (16, +1.013), 2000 (8, +461) y 2015 (26.356, −43.291). Ninguna aborta la carga.

### Conteos post-recarga (antes de la limpieza)

| Tabla | Filas |
| --- | ---: |
| `party` | 549 |
| `party_election` | 2.106 |
| `vote` | 6.047.666 |
| `turnout` | 708.023 |
| `poll_result` | 6.125 |

Hechos idénticos a los pre; `party` aún con las filas viejas (28 quedaron huérfanas al fusionarse las candidaturas).

Consultas de comprobaciones antes de la limpieza: 27 grupos por puntuación (las filas viejas sin candidaturas) y 7 filas para `BNG`/`UPL`/`FIA`/`Cs`/`PP`/`PSOE`/`IU` (las fusionadas ya apuntan a la fila canónica).

### Limpieza de huérfanos (T6)

Filas huérfanas detectadas (28; mismo predicado que el `DELETE`, sin `party_election` ni `poll_result`):

```text
19 f-i-a (F.I.A.) · 32 u-p-l (U.P.L.) · 48 b-n-g (B.N.G.) · 135 fe-i (FE (I))
173 e-u (E U) · 178 fe-a (FE (A)) · 186 uni-d-a (UNI.D.A) · 261 lv-cm (LV-CM)
310 l-i-lit-ci (L.I. (LIT-CI)) · 311 lv-e (LV-E) · 333 a-u-n (A.u.N.)
344 c-d-s (C.D.S.) · 345 c-s (C's) · 350 d-n (D.N.) · 351 e-v-a-v (E.V.-A.V.)
354 i-u (I.U.) · 357 f-a (F.A.) · 362 i-m-c (I.M.C.) · 363 li-litci (LI-LITCI)
369 p-c (P.C.) · 372 p-c-p-e (P.C.P.E.) · 378 p-s-o-e (P.S.O.E.)
381 p-o-s-i (P.O.S.I.) · 382 p-p (P.P.) · 383 p-r-gu (P.R.GU.)
395 u-r-c-l (U.R.C.L.) · 425 p-r-c (P.R.C.) · 536 i-fem (I.Fem)
```

Comando (SQL revisable de `design.md`, con las dos exclusiones):

```sql
DELETE FROM silver.party p
WHERE NOT EXISTS (
        SELECT 1 FROM silver.party_election pe WHERE pe.party_id = p.id)
  AND NOT EXISTS (
        SELECT 1 FROM silver.poll_result pr WHERE pr.party_id = p.id);
```

Salida: **`DELETE 28`** (exit code 0).

### Conteos finales

| Tabla | Filas |
| --- | ---: |
| `party` | 521 |
| `party_election` | 2.106 |
| `vote` | 6.047.666 |
| `turnout` | 708.023 |
| `poll_result` | 6.125 |

Las filas de `party` referenciadas solo por sondeos se preservaron: `salf` (391 resultados) y `alianca-cat` (21) siguen en `silver.party`.

### Comprobaciones finales (las cuatro de `design.md`)

**1. Procesos `congress` nacionales con candidaturas y votos — 13:**

```text
 procesos
----------
       13
(1 row)
```

**2. Grupos por puntuación — 0 filas:**

```text
 slugs | count
-------+-------
(0 rows)
```

**3. Marcas clave — exactamente 7 filas, una por marca:**

| `slug` | `name` | procesos |
| --- | --- | ---: |
| `bng` | BNG | 11 |
| `cs` | Cs | 5 |
| `fia` | FIA | 3 |
| `iu` | IU | 7 |
| `pp` | PP | 12 |
| `psoe` | PSOE | 12 |
| `upl` | UPL | 8 |

**4. Huérfanos — 0:**

```text
 count
-------
     0
```

## Trazabilidad

| Requirement | Test / evidencia |
| --- | --- |
| R1 — resolución por `PartyResolver` | `test_two_processes_one_party` |
| R2 — dos grafías, una fila de `party` | `test_two_processes_one_party` |
| R3 — ficha del catálogo sin `unknown party label` | `test_two_processes_one_party` |
| R4 — alta con warning | `test_unknown_head_label_warns` |
| R5 — recarga sin duplicar `party` | `test_force_reload_preserves_facts` |
| R6 — hechos conservados en `--force` | `test_force_reload_preserves_facts` |
| R7 — 13 procesos con candidaturas y votos | Evidencia SQL (§«Comprobaciones finales»: 13; 13/13 `processed` en §«Recarga») |
| R8 — 0 grupos por puntuación | Evidencia SQL (§«Comprobaciones finales»: 0 filas) |
| R9 — 7 marcas en una fila | Evidencia SQL (§«Comprobaciones finales»: 7 filas) |
| R10 — 0 huérfanos (preservando `poll_result`) | Evidencia SQL (§«Comprobaciones finales»: 0; `salf` y `alianca-cat` preservadas) |
| R11 — `data-model.md` describe `parties.py` + catálogo | `test_docs_data_model` |
| R12 — `data-model.md` sin «provisional» | `test_docs_data_model` |
| R13 — `ingesta.md` describe `parties.py` + catálogo | `test_docs_ingesta` |
| R14 — `ingesta.md` sin «provisional» | `test_docs_ingesta` |
| R15 — `ingestor/AGENTS.md` lista ambos ficheros | `test_docs_ingestor_agents` |

## Decisiones

- **`test_parties.py::test_slugify_single_source`:** la feature 12 afirmaba `election.slugify is slugify`; el diseño de esta feature retira el re-export de `election.py`, así que la aserción pasa a `not hasattr(election, "slugify")` (y se mantiene `polls.slugify is slugify`). Es una consecuencia mecánica del diseño, no un cambio de alcance.
- **Fixtures:** nombres con el patrón real del adaptador `<tipo>02<AAMM>.DAT` (`02020806.DAT`…), no `<tipo><código de proceso>.DAT`; el glob de `find_files` (`{kind}02*.DAT`) lo exige.
- **Catálogo:** sin cambios. La recarga resolvió las 921 cabeceras con 0 altas; no hubo grafías sin ficha que registrar como alias.
- **`polls/loaders/polls.py`:** no se tocó; ya importaba `slugify` de `ingestor.parties` (nunca pasó por el re-export de `election.py`).

## Cambio de criterio (2026-10-19)

- **Qué:** se eliminan del suite `_real_session()` y los cuatro `test_state_*` de `ingestor/tests/test_party_reload.py`. El fichero queda con 6 tests: 3 de integración (`db`) y 3 de documentos.
- **Por qué:** en CI nunca corrían (se saltaban) y dependían del estado operativo local; su valor es evidencia operativa, no un test. Las invariantes R7–R10 se mantienen como verificación manual con el SQL reproducible de `design.md` §«Comprobaciones» y su salida registrada en §«Comprobaciones finales».
- **Trazabilidad:** R7–R10 pasan de «test» a «evidencia SQL» en la tabla de §«Trazabilidad».
