# Review — feature 5 `polls_model`

**Veredicto:** APPROVED

Rama `feature/polls_model` @ `9a409a5d`. `./init.sh` re-ejecutado por el reviewer: verde (28 tests, ruff check/format, `alembic check` sin drift contra el Postgres de `:5434`). Migración única: head `368c5831061d`.

## Trazabilidad requirements ↔ tests

Tests: `ingestor/tests/test_polls_model.py` (16) — todos en verde.

- R1: [x] `test_pollster_pk_name_and_unique_slug` (L49) — PK `id`; `name` Text NOT NULL; `slug` String(60) UK.
- R2: [x] `test_poll_pk_and_required_pollster_fk` (L58) — FK a `silver.pollster.id` NOT NULL.
- R3: [x] `test_poll_source_election_type_and_revision` (L64) — `source` Text, `election_type` String(20), `revision_id` BigInteger, los tres NOT NULL.
- R4: [x] `test_poll_election_fk_is_nullable` (L74).
- R5: [x] `test_poll_fieldwork_and_sample_are_nullable` (L79).
- R6: [x] `test_poll_turnout_is_numeric_with_range_check` (L88) — Numeric(5,2) NULL + CHECK `poll_turnout_range`.
- R7: [x] `test_poll_result_fks_are_indexed` (L98) — FK a `poll.id` y `party.id`, indexadas.
- R8: [x] `test_poll_result_pct_is_numeric_with_range_check` (L106) — CHECK `poll_result_pct_range`.
- R9: [x] `test_poll_result_seats_are_nullable_ints` (L116).
- R10: [x] `test_poll_result_unique_poll_and_party` (L123) — UK (`poll_id`, `party_id`).
- R11: [x] verificación por comando, tal como fija el spec aprobado (`requirements.md` §Nota de verificación L76–79; `design.md` L99: «R11–R12 se verifican por comando, no por pytest»). Reproducido por el reviewer: `alembic upgrade head` aplicado en local (head = `368c5831061d`) e introspección de la BD: existen las 3 tablas con sus columnas, FKs (`poll_pollster_id_fkey`, `poll_election_id_fkey`, `poll_result_poll_id_fkey`, `poll_result_party_id_fkey`), UK (`pollster_slug_key`, `poll_result_poll_id_party_id_key`), CHECKs (`poll_turnout_range`, `poll_result_pct_range`) e índices (`ix_silver_poll_result_poll_id`, `ix_silver_poll_result_party_id`). No se rechaza por «sin test en pytest»: la estrategia de verificación es parte del spec aprobado por el humano, es automatizada, corre en `init.sh` §5 y en `ingestor.yml`, y su objeto de verificación es la propia base de datos.
- R12: [x] ídem — `uv run alembic check` → «No new upgrade operations detected».
- R13: [x] `test_silver_polls_page_has_complete_tables` (L165) + `test_silver_polls_page_dimms_party_and_election` (L194) + `test_drawio_has_a_page_per_schema_and_domain` (L161).
- R14: [x] `test_bronze_polls_page_shows_snapshot_flow` (L202) + L161. Desviación valorada abajo (§Desviación T6/R14).
- R15: [x] `test_data_model_documents_page_per_schema_and_domain` (L215) + `test_data_model_v2_describes_polls_tables` (L221).

## Tasks completas

- T1–T8: [x] — todas marcadas en `specs/polls_model/tasks.md`; correspondencia verificada contra los commits `eb00056f`, `151c1472`, `f8b46de4`, `d2f10fb2`, `7201e145`, `ec7abb27`, `75cf67c3`, `9a409a5d` (uno por task, atómicos).

## Desviación T6/R14 — juicio

**Justificación válida; R14 sigue verificado.**

1. El validador de la skill (`~/.agents/skills/database-erd-drawio/scripts/validate_erd.py`) exige que todo `mxCell` con `edge="1"` use `edgeStyle=entityRelationEdgeStyle` (L179) y que origen y destino del edge sean filas de tabla (`rows`, L188–191). Un edge fichero→caja de tabla sería rechazado con dos errores; el block arrow `shape=step` (`docs/db/schema.drawio` L112, entre el nodo fichero L109 y la caja `ingestion` L118) es la representación disponible para un flujo de datos bajo esas reglas.
2. R14 pide «el flujo … al registro `bronze.ingestion`» sin imponer tipo de conector; el test comprueba los elementos sustantivos: nodo del snapshot (`data/raw/polls/…`), caja `ingestion` atenuada (`opacity=40`) y flecha de flujo. Cubre el requisito tal y como está redactado.
3. Matiz no bloqueante: el test no verifica orientación/posición de la flecha; comprobado en geometría: `bp_arrow` x=540–620 queda entre el fichero (x 40–480) y la caja (x 680–1080), apuntando al este.
4. El ajuste del test de T5 durante T6 está documentado (commit `ec7abb27` y `progress/impl_polls_model.md`); el resto de tests de T5 intacto.

## Checkpoints

- C1: [x] — piezas base del arnés y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#5; validado por `init.sh` §3); features 1–4 `done` con el suite en verde; `progress/current.md` describe la sesión activa.
- C3: [x] — tres sitios sincronizados (ERD «Silver polls» L759–1145 ↔ `models.py` L248–298 ↔ migración `368c5831061d`) y `alembic check` sin drift; ninguna migración ya aplicada editada (solo se añade una), sin DDL a mano; `pyproject.toml`/`uv.lock` intactos (sin dependencias nuevas); sin `print(`/TODO en el diff; arquitectura respetada (hechos en `silver`, sin agregados); logging N/A (no hay código de ejecución nuevo).
- C4: [x] en local — pytest 28/28, `ruff check` y `ruff format --check` limpios, `alembic check` sin drift (re-ejecutado vía `./init.sh`). Sub-item CI: [ ] sin run de `ingestor.yml` para `feature/polls_model` (rama sin pushear, regla de no-push del repo); el workflow ejecuta exactamente estos gates — dispararlo con el push/PR antes de fusionar.
- C5: [ ] pendiente del cierre post-veredicto — repo limpio (solo `opencode.json` modificado por el humano, fuera de los commits de la feature) y documentación de la feature actualizada en commits de la misma rama; faltan los pasos §5 que se ejecutan *tras* esta aprobación: entrada en `progress/history.md` y `feature 5 → done`.
- C6: [x] — spec con los 3 archivos; EARS correcto (un `DEBE` por R, ids estables, tabla acceptance↔R); T1–T8 `[x]`; mapa de trazabilidad en `progress/impl_polls_model.md` (excepción R11–R12 documentada y aceptada arriba).

## Cambios requeridos

Ninguno. Siguiente paso (leader, protocolo §5): cierre de sesión (history + `done`), commit de este review, push/PR para el CI.
