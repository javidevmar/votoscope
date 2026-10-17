# Implementación — `polls_lexer` (feature 7)

Rama `feature/polls-lexer` (stack sobre `feature/polls-fetch`). Working tree, **sin commitear**: el commiteo es el paso final tras el reviewer y el OK del usuario.

## Qué se ha hecho

- `ingestor/src/ingestor/polls/parsers/__init__.py` — paquete nuevo (docstring del dominio).
- `ingestor/src/ingestor/polls/parsers/wikitext.py` — lexer genérico: `Cell`/`Row`/`Table`, `parse_tables`, `clean`; internos `_parse_attrs`, `_split_cell`, `_find_balanced`, `_strip_template`, `_unwrap_smaller`, `_unwrap_font`, `_expand_rowspans`, `_rowspan`. Solo stdlib (`re`, `logging`, `dataclasses`).
- `ingestor/tests/test_wikitext.py` — 24 tests con cadenas sintéticas inline (sin red, sin fixtures).
- `ingestor/AGENTS.md` — bullet de `polls/` documenta `parsers/wikitext.py` (R20).

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican) ni dependencias nuevas. `./init.sh` en verde (ruff check/format, 74 tests, `alembic check` sin drift).

## Trazabilidad

| Requirement | Test(s) |
| --- | --- |
| R1 | `test_parse_tables_one_per_block` |
| R2 | `test_table_attrs_from_opening_line` |
| R3 | `test_closing_line_not_in_rows` |
| R4 | `test_rows_split_on_row_marker` |
| R5 | `test_cell_markers` |
| R6 | `test_cell_attr_value_split`, `test_realistic_party_cell` |
| R7 | `test_row_attrs_dict`, `test_cell_attr_value_split` |
| R8 | `test_rowspan_data_rows`, `test_rowspan_header_rows`, `test_rowspan_three_rows`, `test_rowspan_one_is_noop` |
| R9 | `test_refs_removed`, `test_realistic_party_cell` |
| R10 | `test_efn_removed` |
| R11 | `test_bold_removed`, `test_realistic_party_cell` |
| R12 | `test_smaller_unwrapped` |
| R13 | `test_font_unwrapped`, `test_realistic_party_cell` |
| R14 | `test_br_variants_to_newline`, `test_realistic_party_cell` |
| R15 | `test_text_stripped` |
| R16 | `test_module_is_stdlib_only` |
| R17 | `test_module_has_no_io` |
| R18 | `test_unterminated_table_warns` |
| R19 | `test_parse_tables_one_per_block`, `test_text_outside_blocks_ignored` |
| R20 | `test_docs_ingestor_agents` |

## Notas para el reviewer

- La expansión de `rowspan` distingue los spans que cubren la fila en curso de los registrados por ella para las siguientes; los spans pendientes **por delante** de la última columna se emiten al agotarse las celdas (caso real de la cabecera con `Lead`).
- `clean()` aplica las reglas en bucle hasta punto fijo; cada regla solo sustituye por subcontenido (longitud estrictamente menor), así que termina. Una plantilla truncada (sin `}}`) se deja tal cual.
- Limitaciones documentadas en `design.md`: una celda por línea; `||`, `!!`, `|+`, celdas multilínea y tablas anidadas no se soportan (no existen en la fuente verificada).
