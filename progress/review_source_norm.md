# Review — feature 18 `source_norm`

**Veredicto:** APPROVED

Rama `feature/source-norm`, cambios en el working tree y sin commits. Revisión independiente: `./init.sh` re-ejecutado, inventario de literales recalculado desde los tres `.wikitext` de `data/raw/polls/`, contraste del estado de `silver.poll` contra el Postgres local y lectura del diff completo.

## Verificación independiente

- `./init.sh`: **exit 0** — arnés/specs, `uv sync`, `ruff check`, `ruff format`, **289 pytest** verdes y `alembic check` → «No new upgrade operations detected.» (sin drift). La sección web se omite con `[WARN]` porque `web/node_modules` no existe; la feature no toca `web/`.
- Inventario: los tres snapshots locales (`1380713440`, `1380777984`, `1380859635`) producen **43 literales distintos**, idénticos a la tabla de `specs/018_source_norm/design.md` §«Inventario» y a `SIGNATURE_CASES` de `test_wikipedia_polls.py:369-413`. Ningún `pollster_name` cambia respecto de la regla anterior `_pollster_name` (comparado literal a literal).
- `uv run alembic heads` → `0fa48964369e`; `down_revision = 9f3c2a1b7d40` (`alembic/versions/0fa48964369e_poll_source_roles.py:16`), dos `add_column` nullable y sin `CREATE SCHEMA` (L24-25).
- `silver.poll` en local: 575 filas, 479 con `media`, 54 con `reestimator`, 42 solo encuestadora, `max(revision_id)=1380859635`; spot-check correcto (`CIS (Target Point)` → `NULL`/`Target Point`; `More in Common` → `NULL`/`NULL`; `SocioMétrica/El Español` → `El Español`/`NULL`).
- ERD «Silver polls»: filas `media text` (y=120) y `reestimator text` (y=150) tras `source`, ambas con flag `NULL`, y caja `poll` a 390 (30 + 12 filas × 30); el resto de filas desplazadas +60.

## Trazabilidad requirements ↔ tests

- R1: [x] `test_parse_signature_real_literals` (`test_wikipedia_polls.py:419`, casos con barra) y `test_pollster_name_extraction` (`:349`); `parse_signature` hace `strip` de ambos tramos (`wikipedia_polls.py:304-308`).
- R2: [x] `test_parse_signature_real_literals` (casos `CIS (…)`), `test_pollster_name_extraction` (`:356-360`) y `test_real_cis_block` (`:579`; `:597-601`).
- R3: [x] `test_parse_signature_real_literals` (`Ateneo del Dato`, `CIS`, `More in Common`, `PSOE`, `Sumar`) y `test_pollster_name_extraction` (tercera fila → `(None, None)`).
- R4: [x] `test_parse_signature_combined_and_empty_parts` (`:431`): `Firm/Media (X)` → `Firm`, `Media`, `X`.
- R5: [x] `test_parse_signature_combined_and_empty_parts` (`Firm/` y `CIS ()` → papel nulo + warning `signature part is empty` con el literal); implementación `wikipedia_polls.py:294-303`.
- R6: [x] `PollRow.media`/`reestimator` (`wikipedia_polls.py:82-95`) y aserciones de tríos en `test_pollster_name_extraction`, `test_real_head_first_rows` (`:249-255`) y `test_real_cis_block` (`:597-601`).
- R7: [x] `source` literal intacto: `test_real_head_first_rows` (`:224`, `:234`), `test_real_cis_block` (`:582-586`) y `test_pollster_name_extraction` (`:351-355`); `_read_row` no reescribe `source` (`wikipedia_polls.py:273-283`).
- R8: [x] `test_poll_source_roles_are_nullable_text` (`test_polls_model.py:74`); columnas `Text` nulables en `models.py:277-278`.
- R9: [x] mismo test (declaración en `models.py`) + migración autogenerada `0fa48964369e`, revisada (dos `add_column`, `down_revision` al head previo); sin DDL a mano ni migración existente editada.
- R10: [x] verificación por comando, tal como fija el spec aprobado (`requirements.md:117`, `design.md:144-146`): reproducido por el reviewer vía `./init.sh` §6 → «No new upgrade operations detected.».
- R11: [x] `test_silver_polls_page_has_complete_tables` (`test_polls_model.py:172`) + inspección directa de la página «Silver polls» (filas `media`/`reestimator`, flags `NULL`, orden tras `source` y altura 390).
- R12: [x] `test_data_model_v2_describes_polls_tables` (`test_polls_model.py:230`) + `.agents/data-model.md:40`.
- R13: [x] `test_cli_registers_and_loads` (`test_polls_load.py:125`; `:158` → `("Medio", None)`, `:167` → `(None, "Target Point")`) + loader `polls.py:157-158`.
- R14: [x] `test_reload_roles_is_idempotent` (`test_polls_load.py:236`) + recarga real documentada (575 filas antes y después, mismos tríos).
- R15: [x] `test_parse_signature_real_literals` (`test_wikipedia_polls.py:419`), 43 casos parametrizados que son la unión de los tres snapshots de bronce; inventario recompuesto por el reviewer desde `data/raw/polls/**` y coincidente.
- R16: [x] tests de carga (`test_cli_registers_and_loads`, `test_reload_roles_is_idempotent`), modelo/ERD (`test_poll_source_roles_are_nullable_text`, `test_silver_polls_page_has_complete_tables`, `test_data_model_v2_describes_polls_tables`) y documentos (`test_docs_ingesta`, `test_docs_ingestor_agents`, `test_docs_data_sources_quirks`); además `test_gold.py` (`SILVER_TABLES`) actualizado (desviación justificada en `progress/impl_source_norm.md:121-124`, necesaria para el suite verde).
- R17: [x] `test_docs_data_sources_quirks` (`test_polls_run.py:249`, subcadenas `reestimador`, `Encuestadora/Medio`, `paréntesis`) + `.agents/data-sources.md:140-148`.
- R18: [x] `test_docs_ingesta` (`test_polls_load.py:700`, subcadenas `media`, `reestimator`, `idempotente`, `--force`) + `docs/ingestor/ingesta.md:116-125,139`.
- R19: [x] `test_docs_ingestor_agents` (`test_polls_load.py:717`, subcadena `reestimador`) + `ingestor/AGENTS.md:31`.
- R20: [x] `test_parse_signature_unknown_literal` (`test_wikipedia_polls.py:425`) + 43 literales reales; no hay lista blanca en `src/` (la extracción es regex genérica).

## Tasks completas

- T1–T15: [x] — las 15 tasks de `specs/018_source_norm/tasks.md` están marcadas; correspondencia verificada con el diff: adaptador (`Signature`/`parse_signature`, `PollRow`, `_read_row`), `models.py`, migración, ERD, loader, docs y tests. No hay tasks `[ ]`.

## Checkpoints

- C1: [x] — piezas base y los 4 agentes presentes; `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#18, validado por `init.sh` §3); `progress/current.md` describe la sesión activa.
- C3: [x] — tres sitios sincronizados (ERD ↔ `models.py:277-278` ↔ migración `0fa48964369e`) y `alembic check` sin drift; sin DDL a mano; sin dependencias nuevas (`pyproject.toml`/`uv.lock` intactos); capas respetadas (extracción pura en el adaptador, persistencia en el loader, sin cambios de resolución de partidos); logging con `logger.warning` y formateo perezoso; sin `print()`/TODO en el diff.
- C4: [x] en local — 289 pytest verdes, `ruff check`/`ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para la rama (cambios sin commitear, por diseño del flujo); se disparará con los commits/push tras el OK.
- C5: [ ] pendiente del cierre post-veredicto — sin temporales ni basura en `git status` (solo la migración y `progress/impl_source_norm.md` sin trackear, esperados); `progress/history.md` con la última sesión (17); feature 18 en `in_progress` (correcto); commits atómicos pendientes del OK del usuario.
- C6: [x] — `specs/018_source_norm/` con los 3 archivos; EARS con ids estables y tabla acceptance↔R; T1–T15 `[x]`; mapa R↔test en `progress/impl_source_norm.md` (verificado arriba).

## Observaciones no bloqueantes

1. `progress/impl_source_norm.md:91` dice que `('SocioMétrica/El Español', 'El Español', None)` aparece **×42**; la base da **35** filas con ese literal (y 35 con `media='El Español'`; el 42 es el conteo de `solo_encuestadora` de la consulta anterior). Corregir el número en el informe antes de cerrar; los datos de `silver` son correctos.
2. `feature_list.json` incluye además la entrada 19 `gold_matviews` (`pending`), fuera del alcance de la 18 y no mencionada en `tasks.md` ni en el informe. Parece una edición del leader/usuario previa a la implementación (mtime 20:04, antes del código); confirmarlo y, si no es así, sacarlo del diff de la 18.
3. `ingestor/AGENTS.md:32` enumera tres migraciones y no incluye la nueva `0fa48964369e` (ni la `9f3c2a1b7d40` de la 16); la lista ya era parcial y no es acceptance de la 18, pero conviene ponerla al día al cerrar.
4. El literal desnudo `()` no coincide con `_PARENTHESISED` (`wikipedia_polls.py:44`, `.+?` del design): devuelve `pollster_name='()'` en vez del vacío que menciona `design.md` §«Reglas» punto 4. No hay caso real ni test y el implementer lo documenta (`progress/impl_source_norm.md:129-131`); si se quiere cerrar esa arista, es una decisión de spec (la regex y el ejemplo del design se contradicen), no un defecto de los 43 literales.

## Cambios requeridos

Ninguno.
