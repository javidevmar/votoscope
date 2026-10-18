# Bitácora histórica (append-only)

Las sesiones anteriores al arnés SDD están registradas en `.agents/plans/` y en el historial de git.

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
