# Requisitos — `polls_lexer`

Feature `id 7` de [`feature_list.json`](../../feature_list.json). Alcance: **lexer genérico** de tablas de wikitexto en `polls/parsers/wikitext.py` + tests con casos sintéticos. El lexer no conoce la fuente: las reglas de Wikipedia (secciones y tablas por año, cabecera a dos filas, fechas, partidos) son de la feature 8, y la carga en `silver`, de la 9.

Formas verificadas en el wikitexto real (revisión `1379921971`, 646 KB) que fijan los requisitos: una celda por línea; sin `||`, `!!`, `|+` ni tablas anidadas; 1185 atributos, todos con comillas (`rowspan="2..4"`, `colspan="N"`, `style="…"`); `<br/>` (5252) y `<br />` (2); `<ref>…</ref>` (642 cierres) y `<ref …/>` (143); `{{efn|…}}`, `{{efn|name="X"|…}}` y `{{efn|name="X"}}`; `{{smaller|X}}`; `{{font|…|text=X}}`.

## R1

CUANDO `parse_tables` recibe un texto con uno o más bloques `{|…|}`, el sistema DEBE devolver una tabla por bloque, en el orden en que aparecen.

## R2

El sistema DEBE exponer como atributos de la tabla los pares `clave="valor"` de la línea de apertura `{|`.

## R3

El sistema DEBE cerrar cada tabla en la línea `|}` y NO DEBE incluir esa línea en las filas de la tabla.

## R4

El sistema DEBE dividir cada tabla en filas: cada línea que empieza por `|-` abre una fila nueva, y las celdas anteriores al primer `|-` forman la primera fila.

## R5

El sistema DEBE reconocer como celda cada línea que empieza por `|` o `!`, marcando las de `!` como de cabecera (`header`) y las de `|` como de datos.

## R6

CUANDO una celda contiene un `|` de primer nivel (fuera de `{{…}}`, `[[…]]` y etiquetas `<…>`), el sistema DEBE tratar el texto anterior a ese `|` como atributos de la celda y el posterior como su valor.

## R7

El sistema DEBE extraer los atributos de fila (texto que sigue a `|-`) y de celda (prefijo anterior al `|` de primer nivel) como pares `clave="valor"` y exponerlos en el modelo resultante.

## R8

CUANDO una celda lleva `rowspan="N"` con N mayor que 1, el sistema DEBE repetir esa celda (mismo texto) en las N−1 filas siguientes, en la misma posición de columna, de modo que las filas expandidas mantengan la alineación de columnas.

## R9

El sistema DEBE eliminar del texto de las celdas las referencias `<ref…>…</ref>` y `<ref…/>` completas.

## R10

El sistema DEBE eliminar del texto de las celdas las notas al pie `{{efn|…}}` completas, incluidas sus variantes con `name=` y su contenido anidado.

## R11

El sistema DEBE eliminar del texto de las celdas los marcadores de negrita `'''`.

## R12

CUANDO el texto de una celda contiene `{{smaller|X}}`, el sistema DEBE sustituirlo por `X`.

## R13

CUANDO el texto de una celda contiene `{{font|…|text=X}}`, el sistema DEBE sustituirlo por `X`, incluida la cadena vacía cuando `text=` está vacío.

## R14

CUANDO el texto de una celda contiene un salto `<br>`, `<br/>` o `<br />`, el sistema DEBE representarlo como un salto de línea (`\n`).

## R15

El sistema DEBE eliminar los espacios en blanco sobrantes al principio y al final del texto de cada celda.

## R16

El sistema DEBE implementar el lexer en `polls/parsers/wikitext.py` usando únicamente la biblioteca estándar, sin dependencias nuevas.

## R17

Las funciones públicas del lexer DEBEN ser puras (sin red ni acceso a disco), de modo que los tests las ejerciten con casos sintéticos inline, sin ficheros de fixture, sin `refs/` y sin red.

## R18

SI un bloque `{|` no tiene su `|}` antes del final del texto ENTONCES el sistema DEBE devolver la tabla con las filas leídas hasta el final y registrar un warning.

## R19

El sistema DEBE ignorar el texto que queda fuera de los bloques `{|…|}` (encabezados de sección, párrafos y demás contenido de la página).

## R20

El sistema DEBE actualizar `ingestor/AGENTS.md` (sección «Ficheros») para documentar `polls/parsers/wikitext.py`.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «`polls/parsers/wikitext.py` tokeniza bloques `{|…|}`, filas `|-` y celdas `|`/`!` y expande `rowspan` a las filas siguientes» | R1, R2, R3, R4, R5, R6, R7, R8, R19 |
| «limpieza: `{{efn|…}}`, `<ref>…</ref>`, `'''`, `{{smaller|X}}`→X, `{{font|…|text=X}}`→X y `<br>`» | R9, R10, R11, R12, R13, R14, R15 |
| «tests con casos sintéticos de cada construcción (sin red)» | R16, R17 |
| Extra: regla de documentación de `ingestor/AGENTS.md` (módulo nuevo de `parsers/` documentado en el mismo commit) | R20 |
| Extra: robustez ante deriva del formato wiki (warning y a seguir) | R18 |

## Nota de verificación

- R1–R15, R18, R19: tests en `ingestor/tests/test_wikitext.py` con cadenas sintéticas inline (una construcción por test; caso combinado tipo CIS al final); ningún test usa red ni fixtures.
- R16: test que comprueba que `polls/parsers/wikitext.py` no importa nada fuera de la biblioteca estándar.
- R17: test que lee el fuente del módulo y comprueba que no contiene acceso a red ni a disco (`urlopen`, `socket`, `requests`, `open(`).
- R18: `caplog` a nivel WARNING con la subcadena fijada en `design.md`.
- R20: test que lee `ingestor/AGENTS.md` y comprueba las subcadenas fijadas en `design.md`.
