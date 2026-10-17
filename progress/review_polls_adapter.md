# Review — feature 8 `polls_adapter`

**Veredicto:** APPROVED

Rama `feature/polls-adapter` (stack sobre `feature/polls-lexer`), working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). `./init.sh` re-ejecutado por el reviewer: verde — arnés + specs, `ruff check`/`ruff format --check` limpios, 99 tests (25 nuevos de `test_wikipedia_polls.py`, todos en verde) y `alembic check` sin drift contra el Postgres de `:5434`.

Diff revisado (solo la feature 8): `ingestor/src/ingestor/polls/adapters/{__init__.py,wikipedia_polls.py}` (nuevos), `ingestor/tests/test_wikipedia_polls.py` (nuevo, 25 tests; nombre fijado en `design.md`, no existe `test_polls_adapter.py`), `ingestor/tests/fixtures/wikipedia_polls/` (6 `.wikitext` nuevas) y `ingestor/AGENTS.md` (bullet de `polls/`). Fuera de alcance y excluidos: `specs/009_polls_load/`, `opencode.json`, `feature_list.json`, `progress/current.md` y `data/raw/` (gitignored). `specs/008_polls_adapter/tasks.md` revisado (solo checkboxes: 18/18).

Verificación adicional del reviewer (sondas puntuales, además del suite):

- Fixtures reales verificadas línea a línea contra el snapshot: `real_2026_head.wikitext` = líneas 13 + 53–383 y `real_2023_tail.wikitext` = líneas 13 + 10149–10182 + 11441–11481 de `data/raw/polls/wikipedia-en/2026-general/1380713440.wikitext` (igualdad exacta; tramos contiguos literales).
- Página completa (575 sondeos; tablas por año: 2/160/180/171/76 filas): solo dos warnings, ambos contemplados — `unknown party column: FA` (R8; subsección «2026 (after FA)») y `unparseable turnout: 66–67` (celda real en snapshot L5533; forma no cubierta por R19 → R22: warning + nulo). Sin `column count mismatch` ni fechas/muestras ilegibles en la página real.
- Ramas sin test ejercitadas a mano: `_parse_seats` con basura (`30.0<br/>abc` → warning `unparseable seats` + escaños nulos conservando `pct`); tabla en subsección de nivel 5 no-año → ignorada; fila con más celdas que la cabecera → warning `column count mismatch` + saltada.

## Trazabilidad requirements ↔ tests

Tests: `ingestor/tests/test_wikipedia_polls.py` (25, todos verdes; fixtures + cadenas inline; sin red, `data/raw/` ni `refs/`).

- R1: [x] `test_real_head_first_rows` (L175–203: 14 filas = una por fila de datos, campos y orden de página), `test_party_cells` (L164–172: `results` en orden de columna), `test_real_cis_block` (L448), `test_real_2023_tail_skips` (L206), `test_synthetic_dates` (L231).
- R2: [x] `test_poll_tables_scope` (L43–47: señuelo de `Voting preferences` fuera), `test_poll_tables_years` (L50–56), `test_poll_tables_all_subsections_and_tables` (L59–70: dos subsecciones del mismo año y dos tablas en una).
- R3: [x] `test_color_header_row_ignored` (L150–154: sin warnings de columna y primera fila de datos = SocioMétrica; la fila de colores no se emite).
- R4: [x] `test_fixed_columns_by_label` (L127–131: `Turnout` antes que `Sample size`; muestra y participación correctas por rótulo).
- R5: [x] `test_synthetic_columns_mapping` (L111–124: orden distinto y rótulos por wikilink alt/`link=`/plano), `test_real_head_first_rows`.
- R6: [x] `test_party_columns_mapping` (L102–106: 15 rótulos → slugs), `test_synthetic_columns_mapping`.
- R7: [x] `test_party_columns_mapping` (L107–108: `salf`/«Se Acabó La Fiesta», `alianca-cat`/«Aliança Catalana»).
- R8: [x] `test_unknown_column_warns_and_ignored` (L134–139: `FA` → warning con el rótulo y sin resultado).
- R9: [x] `test_lead_column_ignored_without_warning` (L142–147: sin warning y sin resultado, sintética + real).
- R10: [x] `test_real_2023_tail_skips` (L206–213: separadoras `colspan` fuera; `assert not caplog.records`).
- R11: [x] `test_real_2023_tail_skips` (fila `#EFEFEF` del resultado de 2023 fuera, sin warnings).
- R12: [x] `test_party_cells` (L164–172: número, `<2.0`, `–`, nota sola, `?`), `test_real_head_first_rows`.
- R13: [x] `test_party_cells` (`N`, `N/M`, `?`), `test_real_head_first_rows` (L196–198: rangos 135/137, 103/105).
- R14: [x] `test_party_cells` (`–`/nota sola/`?` sola no producen resultado; `<2.0`+`0` y `?`+`7` sí).
- R15: [x] `test_parse_date_matrix` (L220: día único → inicio = fin), `test_synthetic_dates` (L239–242).
- R16: [x] `test_parse_date_matrix` (L221–224: `10–11 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`, `31 Dec–3 Jan`), `test_synthetic_dates` (cruce → año−1), `test_real_cis_block` (fecha compartida por `rowspan`).
- R17: [x] `test_parse_date_matrix` (L225), `test_synthetic_dates` (L245).
- R18: [x] `test_sample_and_turnout` (L253–260: `1,000` → 1000, `?` → nulo), `test_synthetic_dates`, `test_real_head_first_rows` (L184).
- R19: [x] `test_sample_and_turnout` (`67.6`/`66` → `Decimal`, `?` → nulo), `test_synthetic_dates`, `test_real_head_first_rows` (L195).
- R20: [x] `test_real_cis_block` (L448–465: tres filas del CIS con `source` literal), `test_pollster_name_extraction` (L297–308), `test_real_head_first_rows` (una fila por fila de datos).
- R21: [x] `test_pollster_name_extraction` (`SocioMétrica/El Español` → `SocioMétrica`; `CIS (Target Point)` → `CIS`; `More in Common`), `test_real_cis_block` (L465).
- R22: [x] `test_parse_date_matrix` (basura → warning `unparseable date` + nulas), `test_garbage_cells_warn_and_null` (L371–384: `unparseable sample size`/`turnout`/`pct` + nulos). Rama de escaños sin test: ver observación 1.
- R23: [x] `test_row_mismatch_warns_and_skips` (L387–391: warning `column count mismatch` + fila saltada).
- R24: [x] `test_table_without_fixed_labels_warns_and_skips` (L394–398: warning `not a polls table` + tabla saltada).
- R25: [x] `test_missing_section_warns_and_empty` (L73–78: warning `section not found` + lista vacía).
- R26: [x] `test_election_type` (L157–158: `ELECTION_TYPE == "congress"`).
- R27: [x] `test_module_is_stdlib_only_and_pure` (L416–439: imports ⊆ stdlib ∪ `ingestor.polls.parsers.wikitext`; sin `urlopen`/`socket`/`requests`/`httpx`/`open(`/`sqlalchemy`/`SessionLocal`).
- R28: [x] `test_fixtures_present` (L404–413: las seis) + suite sin red/`data/raw`/`refs/` (grep verificado); literalidad de las reales verificada por el reviewer (arriba).
- R29: [x] `test_docs_ingestor_agents` (L442–445) + diff de `ingestor/AGENTS.md` (bullet de `polls/` con `adapters/wikipedia_polls.py` y «sondeos»).

## Tasks completas

- T1–T18: [x] — todas marcadas en `specs/008_polls_adapter/tasks.md`; diff = solo checkboxes (18/18). Sin tasks `[ ]`.

## Checkpoints

- C1: [x] — piezas base del arnés y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#8; validado por `init.sh` §3); features `done` con el suite en verde (99/99); `progress/current.md` describe la sesión activa.
- C3: [x] — sin cambios de modelo (ni `models.py`, ni drawio, ni Alembic; `alembic check` sin drift → los tres sitios N/A); sin DDL; sin dependencias nuevas (`pyproject.toml`/`uv.lock` intactos; solo stdlib); capas respetadas (reglas de la fuente en `polls/adapters/`, consumo del lexer de la 7, módulo puro sin red/disco/BD); logging por módulo (`getLogger(__name__)`, `wikipedia_polls.py` L22), formateo perezoso y solo warnings, nivel por `LOG_LEVEL`; sin `print()`/TODO (grep en los 4 ficheros).
- C4: [x] en local — pytest 99/99 (25 nuevos), `ruff check` y `ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para `feature/polls-adapter` (sin commits aún, por diseño del flujo); el workflow ejecuta exactamente estos gates y se disparará con los commits/push post-OK.
- C5: [ ] pendiente del cierre post-veredicto — sin archivos temporales ni basura en `git status` (solo los artefactos esperados; `__pycache__`/`.DS_Store` cubiertos por `.gitignore` L2, L36); `progress/history.md` al día al cerrar la sesión; `feature_list.json` coherente; commits atómicos pendientes del OK del usuario (por diseño).
- C6: [x] — `specs/008_polls_adapter/` con los 3 archivos; EARS con ids estables y tabla acceptance↔R; T1–T18 `[x]`; mapa de trazabilidad R1–R29 en `progress/impl_polls_adapter.md`.

## Desviaciones valoradas (no bloqueantes)

1. `real_2026_head.wikitext` excluye la subsección `2026 (after FA)` (el `design.md` describe el corte «desde `====Voting intention estimates====`»). En el snapshot esa subsección no está vacía de tabla: trae las dos filas de cabecera con la columna `FA` sin mapear (sin filas de datos), que dispararía `unknown party column: FA` y rompería la expectativa del propio `design.md` para esta fixture («ausencia de warnings de columna», `test_color_header_row_ignored`). El recorte sigue siendo literal (tramos contiguos, verificado línea a línea) y el caso FA conserva cobertura en `synthetic_columns` (R8). Documentado en `progress/impl_polls_adapter.md` L26.
2. `synthetic_out_of_scope.wikitext` coloca la tabla válida bajo `=====2026=====` (el `design.md` la describía sin subsección de año); necesario para que `poll_tables` la devuelva. Documentado (impl L28).
3. `adapters/__init__.py` vacío, mientras `polls/__init__.py` y `parsers/__init__.py` llevan docstring de dominio — cosmético.

## Observaciones no bloqueantes (no exigen cambios)

1. R22 — la rama de escaños (`unparseable seats`, `wikipedia_polls.py` L312–324) no tiene test: `GARBAGE_TABLE` cubre fecha/muestra/turnout/pct, pero ninguna celda con segunda línea basura. Comportamiento verificado por sonda del reviewer (`30.0<br/>abc` → warning + escaños nulos, `pct` conservado). Añadir el caso cuando se vuelva a tocar el suite.
2. `unparseable turnout: 66–67` (celda real, snapshot L5533): R19 no cubre rangos de participación y degrada a warning + nulo por R22 (correcto). Anotar en el cotejo de la feature 11.
3. El warning `unterminated table at end of input` del lexer al parsear `real_2026_head` es esperado (corte a mitad de tabla; impl L29) y no es del adaptador; los tests del adaptador no lo confunden con un warning propio.

## Cambios requeridos

Ninguno.

---

## Re-revisión de delta — R8 «opción A» (2026-10-17)

**Veredicto del delta:** APPROVED. Esta sección sustituye a la línea R8 de la revisión original (el resto de la revisión sigue vigente). Rama `feature/polls-adapter`, working tree sin commits.

Alcance del delta (verificado que no toca nada más):

- **Código — `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py`**:
  - `_column_plan` (L221–239): el rótulo no mapeado ya no se descarta; rama desconocida (L236–238) → `logger.warning("unknown party column: %s", label)` (formateo perezoso) + `parties[index] = label` (rótulo crudo como clave). Guards de fijas (L224–226) y `Lead` (L230–233) intactos.
  - `_read_row` (L271–277): itera `plan.parties.items()` con clave genérica `key`; resultados en orden de columna y misma lógica de valores que una columna conocida (R14).
  - `_Plan` (L113–122): docstring documenta el contrato «slug mapeado o rótulo crudo; la identidad la resuelve el loader» (R8).
  - Contraste con las citas de la revisión anterior: `_parse_seats` L312→L317 (+5: docstring de `_Plan` +4 y `parties[index] = label` +1); ningún otro tramo reescrito, sin imports nuevos.
- **Test — `ingestor/tests/test_wikipedia_polls.py`** (el design fija este nombre; `test_polls_adapter.py` no existe):
  - `test_unknown_column_warns_and_kept` (L135–140): `unknown party column` + `FA` en `caplog` y `row.results["FA"].pct == Decimal("5.0")` — warning con el rótulo y resultado conservado con la clave cruda.
  - `test_synthetic_columns_mapping` (L111–125): `"FA"` incluido en el orden de columnas (última de partido, antes de `Lead`).
  - Desplazamiento del fichero +1 línea global (solo la inserción de `"FA"`); las citas de la revisión anterior coinciden (p. ej. `test_real_cis_block` L448→L449, `test_module_is_stdlib_only_and_pure` L416→L417). 25/25 verdes.
  - `ingestor/tests/fixtures/wikipedia_polls/synthetic_columns.wikitext` ya daba `5.0` a `FA` (L27): sin cambios (mtime 22:09, anterior al delta; las seis fixtures intactas).
- **Spec — `specs/008_polls_adapter/`** (contrastado con el código):
  - `requirements.md` R8: «warning con el rótulo + emitir sus resultados con el rótulo crudo como clave» ↔ `_column_plan`/`_read_row` ✓; tabla acceptance↔R y nota de alcance de `FA` (loader la crea, party-norm la cura) coherentes.
  - `design.md`: contrato de `results` (L71: «clave → resultado (slug del mapeo o rótulo crudo de una columna desconocida, R8)») ↔ código ✓; plan de columnas (L87), tabla de warnings (L160) y tabla de tests (L200, `test_unknown_column_warns_and_kept`) actualizados ✓.
  - `tasks.md`: T4 actualizada al comportamiento nuevo; T19 añadida y `[x]`; T1–T19 todas `[x]`.
- **Notas**: `progress/impl_polls_adapter.md` §«Delta R8 (T19)» (L36–40) y `progress/current.md` describen cambio, rename del test y fixture sin cambios — coherentes con lo verificado.

Verificación del reviewer:

- `./init.sh` re-ejecutado: verde — 99 tests, `ruff check`/`ruff format --check` limpios, `alembic check` sin drift (exit 0).
- Sonda de página completa (snapshot `1380713440`, 575 filas): claves con rótulo crudo en `results` = `{}`; los dos únicos warnings de siempre (`unknown party column: FA` de `2026 (after FA)`, sin filas de datos; `unparseable turnout: 66–67`). Las celdas `FA` con valor de la página viven fuera de alcance (`Voting preferences`, `Hypothetical scenarios`) → sin regresión ni claves inesperadas en el snapshot real.
- Trazabilidad R8 vigente: `test_unknown_column_warns_and_kept` + `test_synthetic_columns_mapping` (la línea R8 de arriba queda superada).

Checkpoints: sin cambios respecto a la revisión original; C4 local re-verificado con este `./init.sh`.

Observación no bloqueante: `design.md` L90 describe `_Plan` como «`dict[índice, slug]` de las de partido»; con el delta el valor puede ser slug **o rótulo crudo** (los contratos L71/L87 ya lo dicen). Cambiar «slug» → «clave» cuando se vuelva a tocar el spec.

## Cambios requeridos (delta)

Ninguno.
