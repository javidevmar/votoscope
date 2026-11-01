# Bitácora histórica (append-only)

Las sesiones anteriores al arnés SDD están registradas en el historial de git.

---

## 2026-10-17 — Bootstrap del arnés SDD (OpenCode)

- **Agente:** humano + OpenCode (rama `feature/sdd-harness`).
- **Plan:** portar el arnés de referencia (harness-sdd) a Votoscope con convenciones de OpenCode: cola de features, specs (requirements/design/tasks), subagentes y verificación ejecutable.
- **Cambios:** `AGENTS.md` (reglas, flujo SDD y sección OpenCode), `feature_list.json` (4 features hechas + 10 pendientes), `CHECKPOINTS.md`, `.agents/specs.md`, `.opencode/agents/{leader,spec-author,implementer,reviewer}.md`, `.opencode/commands/{next-feature,close-session}.md`, `opencode.json`, `progress/` e `init.sh`.
- **Verificación:** `./init.sh` verde.
- **Extra:** CI reparada (`astral-sh/setup-uv@v10` → `@v7`; llevaba roja desde el merge de #1) y prosa de ejemplo eliminada de los ficheros del arnés.
- **Cierre:** arnés listo. Siguiente: feature 5 `polls_model` (spec primero; contexto en `.agents/plans/polls-wikipedia.md`).

---

## 2026-10-17 — Feature 5 `polls_model` (modelo silver de sondeos)

- **Agente:** leader + spec-author + implementer + reviewer (rama `feature/polls_model`).
- **Plan:** tarea 1 de la iniciativa abierta [`.agents/plans/polls-wikipedia.md`](.agents/plans/polls-wikipedia.md); spec propio en `specs/polls_model/` (R1–R15, T1–T8) aprobado por el humano antes de implementar.
- **Cambios:** `silver.pollster`, `silver.poll` y `silver.poll_result` en `models.py` + migración `368c5831061d`; 16 tests en `ingestor/tests/test_polls_model.py`; páginas ERD «Silver polls» y «Bronze polls»; `.agents/data-model.md` con la regla «una página por esquema y dominio».
- **Decisiones de revisión:** el enlace `poll.election_id` se materializa con un pase de resolución en `ingest-polls` (primera elección del mismo tipo y ámbito posterior al trabajo de campo; corre en cada ejecución; generaliza a las autonómicas) → plan (decisión 4 y tarea 5) y acceptance de la feature 9. `poll.id` se queda entero (uuid descartado). El reemplazo total de `poll`/`poll_result` por snapshot se mantiene (la mejora «no recargar si el parseo no cambió» queda como fleco documentado del plan).
- **Arnés:** nueva política de commits — el commiteo atómico es el paso final, tras implementar y revisar, y nunca sin el OK explícito del usuario (dos puertas humanas: spec y commit). Docs actualizados: `AGENTS.md` (§3–§5), `.agents/specs.md`, `.agents/style.md`, subagentes, `close-session` y `CHECKPOINTS.md`.
- **Verificación:** `./init.sh` verde (28 tests, ruff, `alembic check` sin drift); `reviewer` **APPROVED** (`progress/review_polls_model.md`; desviación de T6 —block arrow— aceptada). Los cambios se revirtieron a working tree (`git reset --soft main`) para la revisión del usuario y, con su OK, se re-commitearon en atómicos.
- **Cierre:** feature 5 `done`. Siguiente: feature 6 `polls_fetch` (spec primero).

---

## 2026-10-17 — Feature 6 `polls_fetch` + refactor por dominios + specs numeradas

- **Agente:** leader + spec-author + implementer + reviewer (rama `feature/polls-fetch`, stack sobre `feature/polls`).
- **Cambios:** `polls/fetch.py` (resolución de la revisión por API + descarga de la revisión fija; solo stdlib) y subcomando `fetch-polls [--page]`; 22 tests sin red con fixtures reales de la API (revid `1380713440`); docs (`architecture.md`, `ingestor/AGENTS.md`, `ingesta.md`).
- **Refactor (petición del usuario):** ingestador dividido por dominios — `elections/` (parsers/adapters/loaders movidos con `git mv`) y `polls/`; imports, tests y docs actualizados; sin cambios funcionales.
- **Arnés (petición del usuario):** specs numeradas a 3 cifras (`005_polls_model`…; regla en `spec-author.md`), `specs.md`, `init.sh` y `CHECKPOINTS.md` al día.
- **Verificación:** `./init.sh` verde (50 tests, ruff, `alembic check` sin drift); reviewer **APPROVED** (`progress/review_polls_fetch.md`; fixtures verificadas en vivo contra la API). El refactor se commiteó tras el review (movimiento mecánico verificado).
- **Cierre:** feature 6 `done`; stack: `feature/polls` → `feature/polls-fetch` (PR) → `feature/polls-lexer` (spec 7 aprobada). Siguiente: implementar la 7.

---

## 2026-10-17 — Feature 7 `polls_lexer` (lexer genérico de wikitexto)

- **Agente:** leader + implementer + reviewer (rama `feature/polls-lexer`, stack sobre `feature/polls-fetch`).
- **Cambios:** `polls/parsers/wikitext.py` (279 líneas: `Cell`/`Row`/`Table`, `parse_tables`, `clean`; solo stdlib) y 24 tests sintéticos sin red (`tests/test_wikitext.py`); bullet del lexer en `ingestor/AGENTS.md`.
- **Verificación:** `./init.sh` verde (74 tests, ruff, `alembic check` sin drift); reviewer **APPROVED** con sondas adversariales (rowspans solapados, plantillas anidadas, bloque sin cierre). Limitaciones documentadas: attrs con `|` entre comillas y tablas anidadas malformadas (inexistentes en la fuente).
- **Cierre:** feature 7 `done`; PR del stack (piso 3) con spec + implementación. Siguiente: feature 8 `polls_adapter` (spec aprobada por el usuario).

---

## 2026-10-17 — Feature 8 `polls_adapter` (adaptador de Wikipedia) + opción A (columnas desconocidas)

- **Agente:** leader + implementer + reviewer (rama `feature/polls-adapter`, stack sobre `feature/polls-lexer`).
- **Cambios:** `polls/adapters/wikipedia_polls.py` (secciones y tablas por año, cabecera a dos filas, columnas por rótulo, fechas, CIS/reestimaciones, 15 partidos); 25 tests + 6 fixtures (recortes reales del snapshot `1380713440` — descargado con `fetch-polls` — + sintéticas); docs.
- **Decisión del usuario (opción A):** la columna de partido desconocida ya no se descarta — warning + resultados con el rótulo crudo; la resolución de identidad pasa al loader (feature 9, R31) y la curación fina al catálogo de party-norm (features 12–14 encoladas; delivery renumerada a 15–17).
- **Caso real:** la página ya trae la columna `FA` (Broad Front); antes se perdía, ahora fluye y se dará de alta como `fa`/«FA».
- **Verificación:** `./init.sh` verde (99 tests, ruff, `alembic check` sin drift); reviewer **APPROVED**, incluido el re-review del delta R8.
- **Cierre:** feature 8 `done`. Siguiente: feature 9 `polls_load` (spec con R31 pendiente de aprobación).

---

## 2026-10-17 — Feature 9 `polls_load` (carga bronce→plata) + carga real de los sondeos

- **Agente:** leader + implementer + reviewer (rama `feature/polls-load`, stack sobre `feature/polls-adapter`).
- **Cambios:** `polls/loaders/polls.py` (registro bronce, transacción de plata, guard por revisión, pase de resolución, validaciones) + subcomando `ingest-polls [ruta] [--force]`; `tests/conftest.py` (esquemas Postgres aislados `polls_test_*`); 26 tests; docs.
- **Carga real (petición original):** `fetch-polls` (revisión nueva de la tarde: `1380777984`) + `ingest-polls` sobre el Postgres local → **575 sondeos, 6.125 resultados, 28 encuestadoras** (trabajo de campo 24-jul-2023 → 11-oct-2026); partidos nuevos `salf`, `alianca-cat` y `fa` (rótulo crudo de la columna desconocida — opción A funcionando en vivo). `election_id` nulo (la de 2026 aún no existe; el pase la enlazará solo).
- **Verificación:** `./init.sh` verde (125 tests, sin skips — Postgres real); reviewer **APPROVED** (incluida prueba en seco sobre la página real: 575 filas/6.125 resultados sin errores de validación).
- **Cierre:** feature 9 `done`. Siguiente: 10 `polls_schedule` (spec esperando aprobado) y 11 `polls_run` (spec en redacción).

---

## 2026-10-18 — Migración del arnés: plans → specs (features 12–14)

- **Agente:** leader + spec-author (rama `feature/plans-to-specs`, cima del stack).
- **Cambios:** specs `012_party_catalog`, `013_party_reload` y `014_party_polls` redactados desde el plan `party-norm` (quedan `spec_ready`); `.agents/plans/` eliminado y lo durable plegado a `.agents/data-model.md` (identidad de partidos) y `status.md`; referencias limpias en specs 005–011, `feature_list.json`, `AGENTS.md`, `style.md`, `specs.md`, `spec-author.md`, `init.sh` y docstrings de los loaders.
- **Cierre:** rama/PR del stack (`feature/plans-to-specs`). Siguiente: aprobado de los specs 10–14.

---

## 2026-10-18 — Features 10 `polls_schedule` y 11 `polls_run` (en serie)

- **Agente:** leader + implementer + reviewer (ramas `feature/polls-schedule` y `feature/polls-run`, stack sobre `feature/polls-load`).
- **Feature 10 (`done`, rama `feature/polls-schedule`):** el job 2×/día es el encadenado `fetch-polls && ingest-polls`; documentado en `.agents/environment.md` (crontab `0 6,18 * * *` con el log de toda la cadena, exit codes, launchd, provisional → workflow) y esqueleto `.github/workflows/polls-sync.yml` (`schedule:` + `workflow_dispatch`, placeholder sin DB). 5 tests del ciclo «sin novedades» y de los artefactos. Reviewer con una ronda (YAML inválido, redirect fuera de la cadena, subcadenas); **APPROVED**.
- **Feature 11 (`done`, rama `feature/polls-run`):** ejecución real `fetch-polls` + `ingest-polls` sobre el Postgres local (rev. `1380859635`): bronce `processed`; silver 575 sondeos / 6.125 resultados / 28 encuestadoras, anualidades 2023–2026 (campo desde 24-jul-2023). Informe `docs/ingestor/polls-run.md` (589 declaradas = 575 cargadas + 14 saltadas; SQL reproducible; fuera de alcance; avisos `FA`/`FV`; participación `66–67` → nula; cotejo de 6 sondeos) y sección «Sondeos (Wikipedia)» en `.agents/data-sources.md` (formato, rarezas, CC BY-SA + `oldid`). 8 tests de estado/documentos. Reviewer con una ronda (enlace roto, test reforzado, T7 y estado del arnés); **APPROVED**.
- **Arnés:** ejecución «en serie» con dos `in_progress` transitorios — gate `./init.sh` rojo hasta cerrar la 10; resuelto con su cierre y el rebase de `feature/polls-run` encima.
- **Verificación:** `./init.sh` verde (138 tests, ruff, `alembic check` sin drift). Sin push (pendiente del OK del usuario para el stack).
- **Cierre:** features 10 y 11 `done`. Siguiente: tu aprobado de los specs 12–14 (`party-norm`; ya en `spec_ready`) para implementarlas en serie.

---

## 2026-10-19 — Iniciativa `party-norm`: features 12, 13 y 14 (stack lineal)

- **Agente:** leader + implementer + reviewer (ramas `feature/party-catalog`, `feature/party-reload` y `feature/party-polls`, stack `main ← party-catalog ← party-reload ← party-polls` con `gh stack`).
- **Feature 12 `party_catalog` (`done`, rama `feature/party-catalog`):** `src/ingestor/parties.py` (`normalize`, `slugify` única, `Catalog`, `load_catalog`, `PartyResolver`) y `src/ingestor/data/party_catalog.toml` (79 fichas: marcas del 2023, 15 etiquetas de sondeos, parejas punteadas y familias; alias solo donde la normalización no coincide). 43 tests sin red ni BD. Auditoría de grafías anteriores sobre los 13 procesos: 921 cabeceras → **0 altas**, 0 grupos duplicados; 28 filas legadas quedan huérfanas para la 13. Reviewer **APPROVED**.
- **Feature 13 `party_reload` (`done`, rama `feature/party-reload`):** `_resolve_parties` por `PartyResolver`/`load_catalog` (sin slug provisional; `slugify` deja de re-exportarse), fixtures sintéticas `tests/fixtures/party_reload/` y `tests/test_party_reload.py` (integración; R7–R10 quedan como verificación SQL documentada, sin test de estado). Recarga `--force` de los 13 procesos: exit 0, 13/13 `processed`, **0 `unknown party label`**, hechos idénticos; `DELETE 28` huérfanos → **`party` 549 → 521**; 0 grupos por puntuación, 7 marcas clave en una fila, 0 huérfanos. Docs: `.agents/data-model.md`, `docs/ingestor/ingesta.md`, `ingestor/AGENTS.md`. Reviewer **APPROVED**.
- **Feature 14 `party_polls` (`done`, rama `feature/party-polls`):** adaptador por `Catalog.lookup` (`parse_polls(wikitext, catalog=None)`; fuera `PARTY_COLUMNS`/`PartyColumn`), loader por `PartyResolver` (fuera `_PARTY_NAMES`/`_party_slug`), `tests/test_party_polls.py` + adaptaciones de `test_wikipedia_polls.py`/`test_polls_load.py`, `docs/ingestor/ingesta.md`. Recarga real `ingest-polls --force`: 575 `poll` / 6.125 `poll_result` / 521 `party` idénticos, 0 `unknown party label`, encaje 1:1 de las 15 marcas `poll_result` ↔ `party_election`. Reviewer **APPROVED**.
- **Auditoría de alias (leader, dentro de la 12):** las grafías anteriores resuelven por normalización (no necesitan alias; un alias redundante lo rechaza el catálogo). Fuera de la curación inicial: la familia de Coalición Canaria (`CC`/`CC-PNC`/… vs `CCa`/`CCa-PNC`, serie partida por siglas; candidata a curación futura) y fusiones pre-existentes del slug antiguo que la normalización no puede separar (`+MAS+`/`MAS`; `NA`/`NA+`).
- **Criterio de tests (petición del usuario, en la misma sesión):** fuera los tests de estado que leían el `silver` local (features 11 y 13): se saltan en CI y dependen del estado operativo; las invariantes quedan como SQL reproducible + evidencia. La suite de integración pasa a una BD temporal en la rama aparte `feature/test-infra`.
- **Verificación:** `./init.sh` verde en cada cierre (195 tests al final de la 13/14, ruff, `alembic check` sin drift); los tests de integración corrieron contra el Postgres real (esquemas desechables).
- **Cierre:** features 12–14 `done`; PRs del stack abiertas para revisión. Siguiente: 15 `delivery_gold`, 16 `web_scaffold`, 17 `close_minor`, 18 `source_norm`.

---

## 2026-10-29 — Feature 15 `delivery_gold` (vistas gold y contrato con el frontend)

- **Agente:** leader + implementer + reviewer (rama `feature/delivery-gold`, apilada sobre `feature/party-polls`).
- **Cambios:** seis vistas de solo lectura en `gold` (`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat`, `poll_trend`) declaradas en `models.py` (`info={"view": True}`) y creadas por la migración `bcd8a7409aec` desde `gold.py` (`view_ddl()`, única fuente del SQL); `include_object` en `alembic/env.py`; contrato `docs/db/gold.md`; página «Gold» del ERD; topología de entornos (local / Vercel + Neon + GitHub Actions, sin staging) y docs de ingesta/arquitectura/modelo al día. Curación de `party.color` en el catálogo (24 fichas, validación `#rrggbb`) y materialización por el resolver: recarga real de los 13 procesos y de los sondeos (575 sondeos, 15/15 marcas de sondeos con color).
- **Review:** APPROVED. Rondas: separación de alcance de los specs 16–18 (decisión del usuario: se quedan en la rama) y refuerzo de tests (orden completo de `poll_trend`, nombres de geografía en `station_turnout`, comparación de colores con el catálogo).
- **Verificación:** `./init.sh` verde (224 tests, ruff check/format, `alembic check` sin drift); datos reales contrastados (13 elecciones, 2023: censo 37.469.141, participación 66,60; 575 sondeos / 6.125 resultados).
- **Cierre:** feature 15 `done`; commits atómicos y push de `feature/delivery-gold` (sin PR). Siguiente: 16 `web_scaffold`.

---

## 2026-10-31 — Feature 16 `web_scaffold` (Next.js, BFF y rol de solo lectura)

- **Agente:** leader + implementer + reviewer (rama `feature/web-scaffold`, apilada sobre `feature/delivery-gold`).
- **Cambios:** scaffold Next.js 16.4.3 (App Router, TS, pnpm 10.28, Tailwind 4, shadcn/ui) con portada (última elección + resultados nacionales) y logging `LOG_LEVEL`; **BFF obligatorio** en `app/api/` (`_lib/db.ts`, `_lib/gold.ts`, `_lib/params.ts` + Route Handlers `latest-election` y `national-results`), única frontera de datos, con tests estructurales que fallan si hay SQL o `pg` fuera de `app/api/`; migración `9f3c2a1b7d40_web_readonly_role.py` (rol `votoscope_web`, `SELECT` solo en `gold`, privilegios por defecto, sin contraseña) y `ingestor/tests/test_web_role.py`; `web/README.md` y `web/AGENTS.md` como guía y constitución; `.agents/` (architecture, conventions, environment, style) y `init.sh` con la sección web.
- **Review:** APPROVED. La primera ejecución del implementer quedó interrumpida por un reinicio; se retomó sin rehacer el scaffold.
- **Verificación:** `./init.sh` verde (231 tests pytest + 24 de `node --test`, lint y `alembic check` sin drift); `pnpm build` sin base y smoke del BFF (`/api/gold/latest-election`).
- **Cierre:** feature 16 `done`; commits atómicos en `feature/web-scaffold`, sin push ni PR. Siguiente: 17 `close_minor`.
