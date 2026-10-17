# Implementación — `polls_model` (feature 5)

- **Rama:** `feature/polls_model` · **Fecha:** 2026-10-17 · **Agente:** implementer
- **Estado:** T1–T8 completadas; `./init.sh` en verde (28 tests, ruff, `alembic check` sin drift).
- Pendiente: reviewer (no marco `done`).

## Commits

1. `eb00056f` `test(polls_model): add silver polls metadata tests (T1, red)`
2. `151c1472` `feat(polls_model): add pollster, poll and poll_result silver tables (T2)`
3. `f8b46de4` `feat(polls_model): add polls model migration (T3)` — `368c5831061d`
4. `d2f10fb2` `chore(polls_model): verify alembic check has no drift (T4)`
5. `7201e145` `test(polls_model): add doc-sync tests for ERD and data-model (T5, red)`
6. `ec7abb27` `feat(polls_model): add Bronze polls and Silver polls ERD pages (T6)`
7. `75cf67c3` `docs(polls_model): one ERD page per schema and domain (T7)`
8. `chore(polls_model): close T8 with green init.sh` (T8)

## Trazabilidad R↔test

| Req | Verificación |
| --- | --- |
| R1 | `test_pollster_pk_name_and_unique_slug` |
| R2 | `test_poll_pk_and_required_pollster_fk` |
| R3 | `test_poll_source_election_type_and_revision` |
| R4 | `test_poll_election_fk_is_nullable` |
| R5 | `test_poll_fieldwork_and_sample_are_nullable` |
| R6 | `test_poll_turnout_is_numeric_with_range_check` |
| R7 | `test_poll_result_fks_are_indexed` |
| R8 | `test_poll_result_pct_is_numeric_with_range_check` |
| R9 | `test_poll_result_seats_are_nullable_ints` |
| R10 | `test_poll_result_unique_poll_and_party` |
| R11 | migración `368c5831061d` + `uv run alembic upgrade head` contra `:5434`, verificado por inspección de la base (columnas, FKs, UK, CHECKs e índices presentes) |
| R12 | `uv run alembic check` — «No new upgrade operations detected» (paso 5 de `init.sh`) |
| R13 | `test_drawio_has_a_page_per_schema_and_domain`, `test_silver_polls_page_has_complete_tables`, `test_silver_polls_page_dimms_party_and_election` |
| R14 | `test_drawio_has_a_page_per_schema_and_domain`, `test_bronze_polls_page_shows_snapshot_flow` |
| R15 | `test_data_model_documents_page_per_schema_and_domain`, `test_data_model_v2_describes_polls_tables` |

Todos los tests en `ingestor/tests/test_polls_model.py` (16). R11–R12 no se duplican en
pytest, por decisión de `design.md` (la base es el propio objeto de verificación).

## Notas para el reviewer

- **Desviación menor en T6 (flujo de «Bronze polls»):** el flujo snapshot → registro se
  dibuja con la flecha nativa `shape=step` (block arrow), no con una edge. El validador
  de la skill `database-erd-drawio` solo admite edges `entityRelationEdgeStyle` entre
  filas de tablas; un flujo de datos no es una relación entidad-relación. El test de T5
  se ajustó en consecuencia (mismo requisito R14: nodos + flecha + cajas atenuadas).
- **Validación ERD:** cada página nueva validada por separado con
  `scripts/validate_erd.py`: **0 errores / 0 warnings** en ambas. La pasada del fichero
  completo reporta `duplicate id 0`/`1` — preexistente en ficheros multi-página
  (cada página tiene sus raíces `0`/`1`), no introducido por esta feature.
- **Renderizado:** export PNG con draw.io Desktop de las páginas 2 y 4 revisado
  (layouts, atenuaciones y rutas de las edges correctos).
- `opencode.json` (cambio previo del humano) no se ha tocado ni incluido en ningún commit.

## Ficheros

- `ingestor/src/ingestor/models.py` — `Pollster`, `Poll`, `PollResult`.
- `ingestor/alembic/versions/368c5831061d_polls_model.py` — autogenerada, aplicada.
- `ingestor/tests/test_polls_model.py` — 16 tests (R1–R10, R13–R15).
- `docs/db/schema.drawio` — páginas «Bronze polls» y «Silver polls».
- `.agents/data-model.md` — regla de páginas + `pollster`/`poll`/`poll_result` en v2.
