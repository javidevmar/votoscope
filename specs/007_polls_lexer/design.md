# Diseño — `polls_lexer`

Feature 7. Plan de iniciativa: [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), §§ «Parser (wikitexto)» (estructura `polls/parsers/wikitext.py` genérico + adaptador por fuente, tres formas de prefijo de celda) y «La fuente» (rarezas verificadas). El lexer **no conoce la fuente**: secciones, cabecera a dos filas, fechas y partidos son de la feature 8.

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica). Sin dependencias nuevas (`re`, `logging` y `dataclasses` son stdlib). Sin excepciones nuevas: módulo puro; el único log es el warning de bloque sin cierre (R18). Sin CLI.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/parsers/wikitext.py` — lexer genérico de tablas |
| crear | `ingestor/tests/test_wikitext.py` — tests sintéticos (R1–R20) |
| modificar | `ingestor/AGENTS.md` — el bullet de `polls/` documenta `parsers/wikitext.py` (R20) |

## Modelo y firmas — `src/ingestor/polls/parsers/wikitext.py`

```python
@dataclass(frozen=True)
class Cell:
    text: str
    header: bool
    attrs: dict[str, str]


@dataclass(frozen=True)
class Row:
    cells: list[Cell]
    attrs: dict[str, str]


@dataclass(frozen=True)
class Table:
    rows: list[Row]
    attrs: dict[str, str]


def clean(text: str) -> str: ...
def parse_tables(wikitext: str) -> list[Table]: ...
```

Internos: `_parse_attrs(prefix) -> dict[str, str]`, `_split_cell(content) -> tuple[str, str]` (prefijo, valor), `_find_balanced(text, start) -> int | None` (cierre `}}` con anidamiento), `_expand_rowspans(rows) -> list[Row]`, `_strip_refs`, `_strip_efns`, `_unwrap_smaller`, `_unwrap_font`.

Detalles que fijan el contrato:

- `_parse_attrs`: `re.finditer(r'(\w+)\s*=\s*"([^"]*)"', prefix)` → dict. Los prefijos de plantilla (`{{Party shading/PP}}`) no aportan pares y quedan fuera del dict. Verificado: los 1185 atributos de la página van entrecomillados (ninguno sin comillas; no se soportan).
- `_split_cell`: recorre el contenido con contadores de `{{`/`}}` y `[[`/`]]` y salta las etiquetas `<…>`; el primer `|` fuera de esos ámbitos separa prefijo y valor. Sin `|` de primer nivel, todo el contenido es valor (`|?`, `| –`, `| [[File:…|link=…|PP]]`).
- `parse_tables`: línea a línea. Fuera de tabla solo `{|` abre; dentro: `|}` (línea exacta tras `strip()`) cierra, `|-` abre fila (atributos = resto de la línea), `|`/`!` añade celda (`!` → `header=True`), cualquier otra línea se ignora. La fuente usa una celda por línea; multilínea, `||`, `!!`, `|+` y tablas anidadas no existen (verificado: 0/0/0/0) y no se soportan — limitación documentada.
- `Table.attrs` sale de la línea `{|` (`class`, `style`); el adaptador podrá filtrar por clase si lo necesita.

## Expansión de rowspan (R8)

`_expand_rowspans` mantiene un mapa `columna → (filas_restantes, Cell)` y recorre cada fila rellenando huecos:

1. Para cada fila, se emiten las celdas en orden de columna: si la columna está ocupada por un `rowspan` vivo, se emite esa celda (y se descuenta); si no, la siguiente celda de la fila.
2. Al emitir una celda con `rowspan="N"` (N ≥ 2) se registra en su columna con N−1 filas restantes.
3. Cuando se agotan las celdas de la fila, se emiten las columnas pendientes en orden ascendente — cubre el caso real de la cabecera (`Lead` con `rowspan="2"` **después** de las columnas de partido).

Cubre los tres casos reales verificados: datos (fecha/muestra del bloque del CIS arrastradas a las reestimaciones), cabecera (`rowspan="2"` en las columnas fijas y en `Lead`) y `rowspan` ≤ 1 sin efecto. La celda arrastrada es la misma `Cell` (frozen): conserva sus `attrs` con el `rowspan`; el adaptador los ignora.

## Limpieza (R9–R15) — `clean`

Secuencia de reglas aplicada en **bucle hasta punto fijo** (las sustituciones pueden exponer construcciones anidadas; cada regla solo sustituye por subcontenido, así que termina):

1. `<ref …/>` → `` (autocierre).
2. `<ref …>…</ref>` → `` (no codicioso, DOTALL).
3. `{{efn|…}}` → `` con búsqueda de llaves balanceadas; cubre `{{efn|…}}`, `{{efn|name="X"|…}}` y `{{efn|name="X"}}`.
4. `<br>`, `<br/>`, `<br />` → `\n` (`re.sub(r"<br\s*/?>", "\n", …)`).
5. `'''` → ``.
6. `{{smaller|X}}` → `X` (contenido tras el primer `|` del cuerpo de la plantilla).
7. `{{font|…|text=X}}` → `X` (valor del parámetro `text=`; vacío → `''`).

Al final, `strip()` (R15).

Por qué `\n` para `<br>` y no espacio ni nada: la celda de partido real `'''31.9'''<br/>{{font|…|text=139}}` debe quedar `31.9\n139`; con espacio quedaría `31.9 139` (ambiguo) y sin nada, `31.9139` (fusiona % y escaños). El adaptador separará `%` y escaños por línea. Una plantilla truncada (sin `}}`) se deja tal cual, sin error.

## Warning (R18)

`logger.warning("unterminated table at end of input")` (subcadena estable para `caplog`). La tabla se devuelve igualmente con las filas leídas.

## Decisiones

- **rowspan en el lexer (no en el adaptador)**: es sintaxis genérica del formato y es imprescindible para la alineación de columnas de la cabecera a dos filas (feature 8); duplicarlo en el adaptador sería lógica de tabla fuera de su sitio.
- **`clean` pública**: permite tests directos por construcción y la reutilizará el adaptador si le hace falta.
- **`\n` como representación de `<br>`** (ver arriba).
- **`attrs` como dict de pares entrecomillados**: suficiente para `rowspan` (expansión), `colspan`/`style` (detección de filas separadoras en la feature 8) y `class` de tabla; los prefijos de plantilla se ignoran.
- **Tablas en orden, sin offsets ni secciones**: el adaptador troceará el wikitexto por encabezados `==` antes de llamar al lexer (decisión de la feature 8); el lexer solo conoce `{|…|}`.
- **Sin logs INFO**: los parsers del repo no registran trazas por celda; solo el warning de R18.
- **Bucle a punto fijo en `clean`**: cubre anidamientos (`{{smaller|…{{font|…}}…}}`) sin regex recursivas.

## Alternativas descartadas

1. **Expandir `rowspan` en el adaptador (feature 8)**: la expansión es del formato, no de la fuente; y la cabecera a dos filas (columnas fijas y `Lead` con `rowspan="2"`) necesita la expansión para alinear **todas** las columnas antes de leer los partidos.
2. **`<br>` → espacio o eliminado**: fusiona el porcentaje con los escaños (`31.9 139` / `31.9139`); el `\n` conserva la separación real de líneas de la celda.
3. **Renderizar a HTML y parsear con una librería** (`BeautifulSoup`, `pandas.read_html`): dependencia nueva (prohibida sin consentimiento) y el plan fija el wikitexto como formato canónico, más pequeño y sin ruido de render.
4. **Regex monolítico por tabla**: no maneja llaves anidadas (`{{party color|…}}` dentro de `style=`, `{{cite web|…}}` dentro de `<ref>`) ni el split atributos/valor; ilegible y frágil.
5. **Devolver el texto crudo de la celda (con atributos y plantillas)**: el adaptador tendría que re-parsear prefijos, y la expansión de `rowspan` no sabría qué celdas arrastrar.
6. **Exponer offsets de tabla o partir por secciones en el lexer**: YAGNI; el adaptador (feature 8) trocea por sección y pasa el texto al lexer.
7. **Soporte de `||`/`!!`, celdas multilínea, `|+` y tablas anidadas**: no existen en la fuente (verificado); se añadirían si una deriva del formato los introduce (warning y a seguir).

## Tests — `ingestor/tests/test_wikitext.py`

Cadenas sintéticas inline (constantes al principio del fichero); sin fixtures, sin red. Tabla de tests previstos:

| Test previsto | Cubre |
| --- | --- |
| `test_parse_tables_one_per_block` (dos bloques + texto alrededor; orden) | R1, R19 |
| `test_table_attrs_from_opening_line` (`class` y `style`) | R2 |
| `test_closing_line_not_in_rows` (nada tras `|}` en la tabla) | R3 |
| `test_rows_split_on_row_marker` (celdas antes del primer `|-` = primera fila; `|- style=` con atributos) | R4, R7 |
| `test_cell_markers` (`!` → `header=True`; `|` → `header=False`) | R5 |
| `test_cell_attr_value_split` (`rowspan="3"\| 1–4 Sep`, `style="…"\| 8.5`, `{{Party shading/PP}}\| 31.9`, link con pipes → sin split, `\|?`) | R6 |
| `test_row_attrs_dict` (`|- style="height:42px;"`) | R7 |
| `test_rowspan_data_rows` (celda arrastrada a la fila siguiente en su columna) | R8 |
| `test_rowspan_header_rows` (`rowspan="2"` al inicio y al final — caso `Lead`) | R8 |
| `test_rowspan_three_rows` (`rowspan="3"` en un bloque tipo CIS) | R8 |
| `test_rowspan_one_is_noop` | R8 |
| `test_refs_removed` (simple, nombrada, autocierre) | R9 |
| `test_efn_removed` (simple, `name=`, con enlaces; celda que es solo nota → `""`) | R10 |
| `test_bold_removed` (`'''31.9'''` → `31.9`) | R11 |
| `test_smaller_unwrapped` (`CIS {{smaller\|(Target Point)}}` → `CIS (Target Point)`) | R12 |
| `test_font_unwrapped` (`135/137`, `(152)`, `?`, vacío) | R13 |
| `test_br_variants_to_newline` (`<br>`, `<br/>`, `<br />`) | R14 |
| `test_text_stripped` (`\| 8.5` → `8.5`) | R15 |
| `test_realistic_party_cell` (combinado: `{{Party shading/PP}}\| '''31.9'''<br/>{{font\|…\|text=139}}` → `31.9\n139`) | R6, R9, R11, R13, R14 |
| `test_module_is_stdlib_only` (imports del módulo dentro de la stdlib) | R16 |
| `test_module_has_no_io` (fuente sin `urlopen`, `socket`, `requests`, `open(`) | R17 |
| `test_unterminated_table_warns` (`caplog` WARNING con `unterminated`; filas leídas) | R18 |
| `test_docs_ingestor_agents` (subcadenas `wikitext.py` y `lexer genérico`) | R20 |

## Documentación (texto pretendido)

`ingestor/AGENTS.md`, bullet de `polls/` (R20): se añade al final de la frase existente: «; `wikitext.py`, lexer genérico de tablas de wikitexto (sondeos de Wikipedia)». El test de docs comprueba las subcadenas `wikitext.py` y `lexer genérico`, no el texto completo.
