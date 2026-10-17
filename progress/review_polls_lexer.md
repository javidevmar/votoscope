# Review — feature 7 `polls_lexer`

**Veredicto:** APPROVED

Rama `feature/polls-lexer` (stack sobre `feature/polls-fetch`), working tree sin commits (el commiteo es el paso final, tras esta aprobación y el OK del usuario). `./init.sh` re-ejecutado por el reviewer: verde — arnés + specs, `ruff check`/`ruff format --check` limpios, 74 tests (24 nuevos de `test_wikitext.py`, todos en verde) y `alembic check` sin drift contra el Postgres de `:5434`.

Diff revisado (solo la feature 7): `ingestor/src/ingestor/polls/parsers/wikitext.py` (nuevo), `ingestor/src/ingestor/polls/parsers/__init__.py` (nuevo), `ingestor/tests/test_wikitext.py` (nuevo), `ingestor/AGENTS.md` (bullet de `polls/`) y `specs/007_polls_lexer/tasks.md` (checkboxes). Fuera de alcance y excluidos: `specs/008_*`, `specs/009_*`, `opencode.json`, `feature_list.json` y `progress/`.

## Trazabilidad requirements ↔ tests

Tests: `ingestor/tests/test_wikitext.py` (24, todos verdes, cadenas sintéticas inline; sin red ni fixtures).

- R1: [x] `test_parse_tables_one_per_block` (L140–144: dos bloques → dos tablas en orden).
- R2: [x] `test_table_attrs_from_opening_line` (L151–156: `class` y `style`).
- R3: [x] `test_closing_line_not_in_rows` (L159–161: `|}` no aparece como fila; la línea siguiente tampoco).
- R4: [x] `test_rows_split_on_row_marker` (L164–166: celdas antes del primer `|-` = primera fila; tres filas).
- R5: [x] `test_cell_markers` (L169–174: `!` → `header=True`, `|` → `False`).
- R6: [x] `test_cell_attr_value_split` (L177–189: rowspan/style/template/link con pipes/`|?`) + `test_realistic_party_cell` (L276–279).
- R7: [x] `test_row_attrs_dict` (L192–194: attrs de `|-`) + `test_cell_attr_value_split` (attrs de celda).
- R8: [x] `test_rowspan_data_rows` (L197–201), `test_rowspan_header_rows` (L204–220, caso `Lead` al final), `test_rowspan_three_rows` (L223–227), `test_rowspan_one_is_noop` (L230–233).
- R9: [x] `test_refs_removed` (L236–239: simple, nombrada con plantilla anidada, autocierre).
- R10: [x] `test_efn_removed` (L242–246: simple, `name=` con enlaces, `name=` solo; celda-solo-nota → `""`).
- R11: [x] `test_bold_removed` (L249–250).
- R12: [x] `test_smaller_unwrapped` (L253–254).
- R13: [x] `test_font_unwrapped` (L257–262: número, rango, `(N)`, `?`, vacío).
- R14: [x] `test_br_variants_to_newline` (L265–268: `<br>`, `<br/>`, `<br />`).
- R15: [x] `test_text_stripped` (L271–273).
- R16: [x] `test_module_is_stdlib_only` (L290–298: AST; `re`, `logging`, `dataclasses`, `__future__` ⊆ stdlib).
- R17: [x] `test_module_has_no_io` (L301–306: sin `urlopen`/`socket`/`requests`/`open(`); el módulo solo usa `re`/`logging`/`dataclasses` (L11–15), sin red ni disco.
- R18: [x] `test_unterminated_table_warns` (L282–287: `caplog` WARNING con `unterminated` + filas leídas).
- R19: [x] `test_parse_tables_one_per_block` + `test_text_outside_blocks_ignored` (L147–148).
- R20: [x] `test_docs_ingestor_agents` (L309–312) + diff de `ingestor/AGENTS.md` (bullet de `polls/` con `parsers/wikitext.py`, lexer genérico).

Verificación adversarial del reviewer (sondas puntuales sobre el módulo, además de los tests):

- R8 con rowspans solapados `[A rs2, B rs3]` / `[C]` / `[D]` → `[[A,B],[A,B,C],[D,B]]`: alineación de columnas correcta.
- R8 con rowspan en columna intermedia y filas incompletas: celda arrastrada en su columna (mismo objeto `Cell`, frozen).
- R9/R10 anidados: `A<ref name="x">{{cite web|url=…|title=…}}</ref>B` → `AB`.
- R12/R13 anidados: `{{smaller|X {{font|…|text=Y}}}}` → `X Y`.
- R18: bloque sin `|}` → un warning + tabla con las filas leídas.

## Tasks completas

- T1–T10: [x] — todas marcadas en `specs/007_polls_lexer/tasks.md`; sin tasks `[ ]`.

## Checkpoints

- C1: [x] — piezas base y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (#7; validado por `init.sh` §3); features `done` con el suite en verde (74/74); `progress/current.md` describe la sesión activa.
- C3: [x] — sin cambios de modelo (ni `models.py`, ni drawio, ni Alembic; `alembic check` sin drift → los tres sitios N/A); sin DDL; sin dependencias nuevas (`re`/`logging`/`dataclasses` de stdlib; `pyproject.toml`/`uv.lock` intactos); capas respetadas (lexer genérico y agnóstico a la fuente en `polls/parsers/`; las reglas de Wikipedia son de la feature 8); logging por módulo (`getLogger(__name__)`, L17) y único warning (L111), nivel por `LOG_LEVEL`; sin `print()`/TODO (grep en los 3 ficheros).
- C4: [x] en local — pytest 74/74 (24 nuevos), `ruff check` y `ruff format --check` limpios, `alembic check` sin drift. Sub-item CI: [ ] sin run de `ingestor.yml` para `feature/polls-lexer` (el único commit de la rama es el spec, fuera del path filter `ingestor/**`); los últimos runs del stack (`feature/polls-fetch`) están verdes y el workflow ejecuta exactamente estos gates — se disparará con los commits post-OK.
- C5: [ ] pendiente del cierre post-veredicto — sin archivos temporales ni basura sin trackear (los `__pycache__` están cubiertos por `.gitignore` L36; `git status` solo lista los artefactos esperados); `progress/history.md` con la última sesión cerrada; commits atómicos pendientes del OK del usuario (por diseño).
- C6: [x] — `specs/007_polls_lexer/` con los 3 archivos; EARS con ids estables y tabla acceptance↔R; T1–T10 `[x]`; mapa de trazabilidad R1–R20 en `progress/impl_polls_lexer.md`.

## Desviaciones valoradas (no bloqueantes)

1. `design.md` listaba internos `_strip_refs`/`_strip_efns`; la implementación usa constantes regex (`_REF_SELF_CLOSING`, `_REF_PAIR`) + `_strip_template` (`wikitext.py` L124–126). La API pública (`Cell`/`Row`/`Table`/`clean`/`parse_tables`) coincide exactamente con el diseño; los internos no son contrato. Documentado en `impl_polls_lexer.md`.
2. `parsers/__init__.py` no figuraba en la tabla de archivos del diseño; es el marcador de paquete (mismo patrón que `polls/__init__.py`). Correcto.

## Observaciones no bloqueantes (no exigen cambios)

1. `_split_cell` no considera comillas al buscar el `|` de primer nivel: un attr con `|` dentro de comillas (`style="a|b"`) partiría mal. El spec verificó que ninguno de los 1185 atributos de la fuente lleva `|`; limitación aceptada en `design.md`.
2. Un `{|` anidado malformado (tabla abierta dentro de otra sin cerrar) acumula las filas del segundo bloque en la primera tabla con warning. Entrada degenerada, inexistente en la fuente (0 tablas anidadas); R18 cubre el bloque sin cierre.
3. `test_module_has_no_io` es una comprobación por subcadenas del fuente (fijada así en `design.md`); suficiente para el contrato de pureza del lexer.

## Cambios requeridos

Ninguno.
