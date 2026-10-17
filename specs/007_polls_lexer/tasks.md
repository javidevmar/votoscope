# Tareas — `polls_lexer`

TDD: cada pareja test → código va en dos tasks consecutivas; cada task es un commit atómico. Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Detalle en [`design.md`](design.md).

- [x] T1 — Crear `ingestor/tests/test_wikitext.py` con las cadenas sintéticas inline y los tests en rojo de tokenización: una tabla por bloque en orden, texto exterior ignorado, atributos de tabla, línea de cierre fuera de las filas, filas (`|-`, primera fila sin `|-`), celdas (`|`/`!` con `header`), split atributos/valor (rowspan, style, `{{Party shading/PP}}`, link con pipes, `|?`) y attrs de fila/celda. Cubre: R1–R7, R19.
- [x] T2 — Implementar en `ingestor/src/ingestor/polls/parsers/wikitext.py` los dataclasses `Cell`/`Row`/`Table`, `_parse_attrs`, `_split_cell` y `parse_tables` (tokenización sin expansión ni limpieza; texto tal cual). `uv run pytest tests/test_wikitext.py` en verde para T1. Cubre: R1–R7, R19.
- [x] T3 — Tests en rojo de la expansión de `rowspan`: datos (celda arrastrada a la fila siguiente en su columna), cabecera (`rowspan="2"` al inicio y al final, caso `Lead`), `rowspan="3"` tipo CIS y `rowspan` ≤ 1 sin efecto. Cubre: R8.
- [x] T4 — Implementar `_expand_rowspans` (mapa columna → (restantes, celda)) y aplicarlo en `parse_tables`. En verde. Cubre: R8.
- [x] T5 — Tests en rojo de la limpieza: `clean()` directo por construcción (refs simple/nombrada/autocierre, efn simple/`name=`/con enlaces, `'''`, `{{smaller|X}}`, `{{font|…|text=X}}` con número/rango/`(N)`/`?`/vacío, `<br>` en sus tres formas, strip) más el caso combinado real-sintético (`{{Party shading/PP}}| '''31.9'''<br/>{{font|…|text=139}}` → `31.9\n139`) y la celda que es solo nota → `""`, vía `parse_tables`. Cubre: R9–R15.
- [x] T6 — Implementar `clean()` (bucle a punto fijo, llaves balanceadas) y conectarlo en `parse_tables`. En verde. Cubre: R9–R15.
- [x] T7 — Tests en rojo de robustez y pureza: bloque sin `|}` → tabla con las filas leídas y `caplog` WARNING con `unterminated`; módulo sin imports fuera de la stdlib; fuente del módulo sin `urlopen`, `socket`, `requests` ni `open(`. Cubre: R16, R17, R18.
- [x] T8 — Implementar el warning de bloque sin cierre y ajustar lo que pidan los tests de T7. En verde. Cubre: R16, R17, R18.
- [x] T9 — Test de documentación (subcadenas `wikitext.py` y `lexer genérico`) y actualizar el bullet de `polls/` en `ingestor/AGENTS.md`. En verde. Cubre: R20.
- [x] T10 — Puerta final: `./init.sh` en verde (ruff, pytest, `alembic check`) y escribir `progress/impl_polls_lexer.md` con la tabla de trazabilidad R1–R20 ↔ tests. Cubre: R1–R20.
