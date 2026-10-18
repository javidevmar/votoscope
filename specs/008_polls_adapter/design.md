# Diseño — `polls_adapter`

Feature 8. Reglas de la fuente de sondeos: tablas por año, cabecera a dos filas, celdas de partido, rarezas y mapeo de partidos (columna desconocida → warning). Consume el lexer genérico de la feature 7 (`polls/parsers/wikitext.py`: bloques, filas, celdas, expansión de `rowspan`, limpieza) y produce las filas que cargará la feature 9. No descarga (feature 6) ni toca la base de datos.

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica). Sin dependencias nuevas (`re`, `logging`, `dataclasses`, `datetime`, `decimal` son stdlib). Sin excepciones nuevas: módulo puro; los casos raros se registran como warnings (R22–R25). Sin CLI.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py` — reglas de la fuente de sondeos |
| crear | `ingestor/tests/test_wikipedia_polls.py` — tests (R1–R29) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/real_2026_head.wikitext` — recorte literal (cabecera + primeras filas de 2026 + bloque del CIS con `rowspan`) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/real_2023_tail.wikitext` — recorte literal (cola de 2023: última fila, separadores y fila de resultado) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_dates.wikitext` — fechas (cruce de año, día único, `?`) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_cells.wikitext` — celdas de partido (`–`, `?`, `<2.0`, rango, nota sola, `<br />`) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_columns.wikitext` — columnas (orden distinto, wikilinks, SALF/Aliança.cat/AA, FA desconocida, Lead, fijas desordenadas) |
| crear | `ingestor/tests/fixtures/wikipedia_polls/synthetic_out_of_scope.wikitext` — tabla señuelo fuera de la sección |
| modificar | `ingestor/AGENTS.md` — el bullet de `polls/` documenta `adapters/wikipedia_polls.py` (R29) |

`tests/fixtures/wikipedia_polls/` ya existe con las fixtures de la feature 6 (`api_revision.json`, `api_missing.json`); no se tocan.

## Firmas nuevas — `src/ingestor/polls/adapters/wikipedia_polls.py`

```python
ELECTION_TYPE = "congress"
POLLS_SECTION = "Voting intention estimates"
FIXED_COLUMNS = ("Polling firm/Commissioner", "Fieldwork date", "Sample size", "Turnout")
LEAD_COLUMN = "Lead"
RESULT_ROW_STYLE = "#EFEFEF"


@dataclass(frozen=True)
class PartyColumn:
    slug: str
    name: str


PARTY_COLUMNS: dict[str, PartyColumn] = {...}  # rótulo resuelto → columna


@dataclass(frozen=True)
class PollResultRow:
    pct: Decimal | None
    seats_min: int | None
    seats_max: int | None


@dataclass(frozen=True)
class PollRow:
    source: str
    pollster_name: str
    fieldwork_start: date | None
    fieldwork_end: date | None
    sample_size: int | None
    turnout: Decimal | None
    results: dict[str, PollResultRow]


def poll_tables(wikitext: str) -> list[tuple[int, Table]]: ...
def parse_polls(wikitext: str) -> list[PollRow]: ...
def parse_date(text: str, year: int) -> tuple[date | None, date | None]: ...
```

Internos: `_split_sections(text)`, `_column_plan(label_cells) -> _Plan`, `_read_row(cells, plan, year)`, `_label(cell_text)`, `_parse_party_cell(text)`, `_parse_seats(text)`, `_parse_sample(text)`, `_parse_turnout(text)`, `_pollster_name(source)`.

Detalles que fijan el contrato:

- `poll_tables` es pública para los tests (R2) y para depurar: devuelve `(año, Table)` del lexer, en orden de página. `parse_polls` la usa y aplana a `PollRow`.
- Los dataclasses se llaman `PollRow`/`PollResultRow` (no `Poll`/`PollResult`) para no chocar con `models.py` en el loader de la feature 9.
- `results` es un diccionario clave → resultado (slug del mapeo o rótulo crudo de una columna desconocida, R8): omite los partidos sin valores (R14), de modo que `len(row.results)` es exactamente «partidos con valor» de la validación de la feature 9. El orden es el de las columnas.

## Flujo de `parse_polls`

1. `_split_sections(wikitext)`: encabezados con `^(={2,6})\s*(.+?)\s*\1\s*$` (MULTILINE); **el cuerpo de una sección termina en el siguiente encabezado de nivel igual o superior** (mismo número de `=` o menos), no en cualquier encabezado — así `====Voting intention estimates====` incluye sus `=====<año>…=====` (si se cortara en cualquier encabezado, el cuerpo quedaría vacío).
2. Se toma la sección de nivel 4 con título exacto `Voting intention estimates`; si no existe → `logger.warning("Voting intention estimates section not found")` y `[]` (R25).
3. Dentro de su cuerpo, subsecciones de nivel 5 cuyo título empiece por cuatro dígitos (`^(\d{4})(\s|$)`): el año sale del título (R16). Cada subsección puede traer una o más tablas.
4. Cada tabla se pasa a `_parse_table(table, year)`; los `PollRow` se acumulan en orden de página (R1).

## Plan de columnas (R3–R9)

- Fila de rótulos: `table.rows[0]`. Si sus celdas no contienen los cuatro rótulos fijos → `logger.warning("not a polls table: missing fixed header labels")` y la tabla se salta (R24).
- Por cada celda de esa fila se resuelve el rótulo con `_label` y se asigna rol:
  - rótulo en `FIXED_COLUMNS` → rol fijo (firm/date/sample/turnout);
  - rótulo `Lead` → ignorada (R9);
  - rótulo en `PARTY_COLUMNS` → columna de partido con su slug;
  - cualquier otro → `logger.warning("unknown party column: %s", label)` y columna con el **rótulo crudo como clave** (R8): el adaptador no inventa slugs; la identidad la resuelve el loader (feature 9).
- Las demás filas de cabecera (la de `{{party color|…}}`) se saltan porque su primera celda es de cabecera (`Cell.header`); la primera fila es la de rótulos (R3).
- `_label(cell_text)`: primer wikilink `[[…]]`; se parte por `|`; último parámetro; si empieza por `link=` se usa su valor; sin wikilink, el texto tal cual. Formas reales: `[[File:Logo del PP (2022).svg|27px|link=People's Party (Spain)|PP]]` → `PP`; `[[File:Adelante Andalucía Isotipo, 2021.svg|30px|link=Adelante Andalucía (2021)]]` → `Adelante Andalucía (2021)`; `[[Se Acabó La Fiesta|SALF]]` → `SALF`.
- `_Plan`: índices de las cuatro columnas fijas + `dict[índice, slug]` de las de partido. Los datos se leen **por índice de columna** una vez construido el plan a partir de la cabecera: el orden de las columnas puede cambiar entre años (R5).

### Mapeo (R6, R7)

| Rótulo resuelto | Slug | Nombre (solo si hay que crear) |
| --- | --- | --- |
| `PP` | `pp` | Partido Popular |
| `PSOE` | `psoe` | Partido Socialista Obrero Español |
| `Vox` | `vox` | Vox |
| `Sumar` | `sumar` | Sumar |
| `ERC` | `erc` | Esquerra Republicana de Catalunya |
| `Junts` | `jxcat-junts` | Junts per Catalunya |
| `EH Bildu` | `eh-bildu` | Euskal Herria Bildu |
| `PNV` | `eaj-pnv` | Euzko Alderdi Jeltzalea-Partido Nacionalista Vasco |
| `BNG` | `bng` | Bloque Nacionalista Galego |
| `CCa` | `cca` | Coalición Canaria |
| `UPN` | `u-p-n` | Unión del Pueblo Navarro |
| `Adelante Andalucía (2021)` | `adelante-andalucia` | Adelante Andalucía |
| `Podemos` | `podemos` | Podemos |
| `SALF` | `salf` | Se Acabó La Fiesta |
| `Aliança.cat` | `alianca-cat` | Aliança Catalana |

El rótulo de Adelante Andalucía es el resuelto del snapshot real (`link=Adelante Andalucía (2021)`); se normaliza como «Adelante Andalucía». Si la wiki renombra el artículo, la columna cae en R8 (warning + rótulo crudo; el loader la da de alta): deriva aceptada. Los nombres solo se usan al crear un partido que falte; los de `salf` y `alianca-cat` los fija este spec.

## Lectura de filas (R10–R14, R20–R21)

Por cada fila después de la de rótulos, en orden:

1. primera celda de cabecera (`Cell.header`) → fila de colores, se salta (R3);
2. `"#EFEFEF" in row.attrs.get("style", "")` → fila de resultado, se salta (R11);
3. una única celda con atributo `colspan` → fila separadora, se salta (R10);
4. número de celdas distinto del de la cabecera → `logger.warning("column count mismatch: %s != %s")` y se salta (R23);
5. se leen firma, fecha, muestra, participación y las celdas de partido por el plan.

- `source` = texto de la celda de firma (ya limpio por el lexer: refs, `{{efn}}`, `{{smaller|…}}`); una fila por fila de datos, reestimaciones del CIS incluidas (`CIS (Opina 360)`, `CIS (Ateneo del Dato)`, `CIS`), cada una con su literal (R20).
- `pollster_name` = texto anterior a la primera `(` o `/`, con `strip` (R21): `SocioMétrica/El Español` → `SocioMétrica`, `CIS (Target Point)` → `CIS`, `More in Common` → `More in Common`.
- Los `rowspan` (bloques del CIS que comparten fecha y muestra) llegan ya expandidos por el lexer: no hay lógica de `rowspan` en el adaptador.

## Fechas — `parse_date(text, year)` (R15–R17)

El año siempre sale de la subsección; las celdas del snapshot real no lo llevan. Formas (con `–`, en dash, como la fuente):

| Celda | Regla |
| --- | --- |
| `5 Oct` | `start = end = date(year, 10, 5)` |
| `10–11 Oct` | mismo mes: `start = date(year, 10, 10)`, `end = date(year, 10, 11)` |
| `29 Sep–1 Oct` | `start = date(year, 9, 29)`, `end = date(year, 10, 1)` |
| `29 Dec–5 Jan` | cruce de año: mes inicial (12) > mes final (1) → `start = date(year - 1, 12, 29)`, `end = date(year, 1, 5)` |
| `?` | `(None, None)` |
| otra | `logger.warning("unparseable date: %s")` y `(None, None)` (R22) |

La «fecha de publicación como aproximación» no necesita código: la fuente ya publica la fecha de publicación cuando desconoce el trabajo de campo, y se guarda igual (día único → inicio = fin). Meses: `Jan`…`Dec` → 1…12.

## Números (R18–R19)

- `_parse_sample`: `?` → `None`; `text.replace(",", "")` → `int`; si no encaja → warning `unparseable sample size` y `None` (R22). Formas reales: `1,000`, `10,104`, `?`.
- `_parse_turnout`: `?` → `None`; `Decimal(text)`; si no encaja → warning `unparseable turnout` y `None` (R22). Formas reales: `67.6`, `66`.

## Celdas de partido (R12–R14)

El lexer convierte `<br/>` en `\n`; por eso el texto de una celda de partido es `pct` o `pct\nescaños`:

1. `lines = text.split("\n")`; `pct` de la primera línea: número → `Decimal`; `?`, `<2.0`, `–`, vacío → `None` (sin warning: son formas conocidas); otra cosa → warning `unparseable pct` y `None` (R22).
2. Segunda línea, si existe: `N` → `(N, N)`; `N/M` → `(N, M)`; `?`, `–`, vacío → `(None, None)`; otra cosa → warning `unparseable seats` y `(None, None)` (R22).
3. Si `pct` y escaños son nulos → la celda no produce resultado (R14): cubre `–` (no listado), `?` (desconocido) y celdas que tras la limpieza son solo una nota (`{{efn|…}}` → `""`). Si hay algún valor, se emite `PollResultRow`.

## Warnings (subcadenas estables para `caplog`)

| Subcadena | Caso | R |
| --- | --- | --- |
| `unknown party column` | rótulo no mapeado (p. ej. `FA`) → se conserva con el rótulo crudo | R8 |
| `not a polls table` | primera fila sin los cuatro rótulos fijos | R24 |
| `column count mismatch` | fila desalineada | R23 |
| `section not found` | falta `Voting intention estimates` | R25 |
| `unparseable date` | celda de fecha rara | R22 |
| `unparseable sample size` | muestra rara | R22 |
| `unparseable turnout` | participación rara | R22 |
| `unparseable pct` | porcentaje raro | R22 |
| `unparseable seats` | escaños raros | R22 |

Sin logs INFO (los parsers del repo no registran trazas por celda; solo warnings).

## Fixtures

Los recortes reales se cortan de un snapshot obtenido con `uv run ingestor fetch-polls` (feature 6; la red se usa una vez al crear la fixture, nunca en los tests), en `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext`. Los cortes son literales (sin retocar); los límites se documentan aquí y en las tasks.

| Fixture | Contenido | Fija |
| --- | --- | --- |
| `real_2026_head.wikitext` | desde `====Voting intention estimates====` hasta la celda `Lead` de la fila oficial del CIS de octubre (tercera del bloque `rowspan="3"`), inclusive: cabeceras de sección, apertura de la tabla, dos filas de cabecera, filas SocioMétrica (`10–11 Oct`, nota de Compromís, `–` en la última columna de partido), Target Point (`6–9 Oct`, rango `135/137`), las intermedias y el bloque del CIS (Opina 360 / Ateneo del Dato / CIS, `rowspan="3"` en fecha y muestra) | cabecera a dos filas, `?`/`–`, rangos de escaños, `rowspan`, reestimaciones CIS, ausencia de warnings de columna |
| `real_2023_tail.wikitext` | cabeceras `====Voting intention estimates====` y `=====2023=====` + apertura de la tabla de 2023 y sus dos filas de cabecera (corte del inicio de la subsección) + cola: última fila de datos (`EM-Analytics/Electomanía`, `24–25 Jul`), fila separadora, fila del resultado de 2023 (`\|- style="background:#EFEFEF;"`), segunda fila separadora y `\|}` (corte contiguo). Es un ensamblado de dos tramos contiguos del snapshot | R10, R11 |
| `synthetic_dates.wikitext` | sección `2026` con tabla mínima (fijas + PP/PSOE + Lead) y tres filas: `29 Dec–5 Jan` (cruce), `5 Oct` (día único), `?`; muestras `1,000`/`?`/`800`; participaciones `?`/`67.6`/`66` | R15–R19 |
| `synthetic_cells.wikitext` | sección `2026` con columnas PP/PSOE/Vox/Sumar/ERC (rótulos planos) y dos filas: `'''32.6'''` + `135/137`; `<2.0` + `0`; `–`; nota sola `{{efn}}`; `2.9` + `<br />` + `?`; y otra con `22.2` sola, `?`+`7`, `?` sola | R12–R14 |
| `synthetic_columns.wikitext` | sección `2026` con las fijas en orden cambiado (`…, Turnout, Sample size`) y columnas `Vox`, `[[File:…\|link=People's Party (Spain)\|PP]]`, `[[Se Acabó La Fiesta\|SALF]]`, `[[File:…\|link=Catalan Alliance\|Aliança.cat]]`, `[[File:Adelante Andalucía Isotipo, 2021.svg\|30px\|link=Adelante Andalucía (2021)]]`, `[[File:Frente AMPLIO.svg\|35px\|link=Broad Front (Spain)\|FA]]`, `Lead`, con valores distintos por columna | R3–R9 |
| `synthetic_out_of_scope.wikitext` | `====Voting intention estimates====` con una tabla mínima (firma `Alpha/Medio`) + `====Voting preferences====` con una tabla señuelo (firma `Decoy/Medio`) | R2 |

Casos de robustez (R22–R25) van como cadenas inline en el test (no necesitan fixture): fila con basura (`??`, `1.000`, `abc`), fila con celdas de menos, tabla sin rótulos fijos y wikitexto sin la sección.

## Tests — `ingestor/tests/test_wikipedia_polls.py`

Sin red; `FIXTURES = Path(__file__).parent / "fixtures" / "wikipedia_polls"`; helper `_fixture(name) -> str`.

| Test previsto | Entrada | Cubre |
| --- | --- | --- |
| `test_fixtures_present` (las seis existen) | — | R28 |
| `test_poll_tables_scope` (señuelo fuera) | `synthetic_out_of_scope` | R2 |
| `test_poll_tables_years` (año de la subsección) | `real_2023_tail`, `synthetic_dates` | R2 |
| `test_missing_section_warns_and_empty` | inline | R25 |
| `test_party_columns_mapping` (15 rótulos/slugs únicos; nombres de SALF y Aliança.cat) | — | R6, R7 |
| `test_synthetic_columns_mapping` (orden distinto; wikilinks; AA por `link=`) | `synthetic_columns` | R5, R6, R7 |
| `test_fixed_columns_by_label` (fijas desordenadas; muestra/participación correctas) | `synthetic_columns` | R4 |
| `test_unknown_column_warns_and_kept` (`FA` → warning + resultado con clave `FA`) | `synthetic_columns` | R8 |
| `test_lead_column_ignored_without_warning` | `synthetic_columns`, `real_2026_head` | R9 |
| `test_color_header_row_ignored` (sin warnings de columna en el recorte real) | `real_2026_head` | R3 |
| `test_party_cells` (`–`, `?`, `<2.0`, rango, nota sola, `<br />`, solo pct, `?`+escaños) | `synthetic_cells` | R12, R13, R14 |
| `test_real_head_first_rows` (SocioMétrica/Target Point/DYM: firma, fechas, muestra, `?`, pct/escaños) | `real_2026_head` | R1, R2, R5, R12–R14, R18, R19, R20 |
| `test_real_cis_block` (tres filas, fuentes literales, fecha/muestra compartidas por `rowspan`) | `real_2026_head` | R16, R20, R21 |
| `test_real_2023_tail_skips` (1 fila; separadoras y resultado fuera; sin warnings) | `real_2023_tail` | R10, R11 |
| `test_parse_date_matrix` (`5 Oct`, `10–11 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`, `31 Dec–3 Jan`, `?`, basura) | inline | R15, R16, R17, R22 |
| `test_synthetic_dates` (cruce → año−1; día único → inicio=fin; `?` → nulas; muestra/participación) | `synthetic_dates` | R15–R19 |
| `test_pollster_name_extraction` (`SocioMétrica/El Español`, `CIS (Target Point)`, `More in Common`) | inline | R21 |
| `test_garbage_cells_warn_and_null` | inline | R22 |
| `test_row_mismatch_warns_and_skips` | inline | R23 |
| `test_table_without_fixed_labels_warns_and_skips` | inline | R24 |
| `test_election_type` | — | R26 |
| `test_module_is_stdlib_only_and_pure` (imports; sin `urlopen`, `socket`, `requests`, `httpx`, `open(`, `sqlalchemy`, `SessionLocal`) | fuente del módulo | R27 |
| `test_docs_ingestor_agents` (subcadenas `wikipedia_polls.py`, `sondeos`) | `ingestor/AGENTS.md` | R29 |

## Decisiones

- **El adaptador consume el lexer (feature 7)**: la tokenización de tablas, `rowspan` y limpieza ya están resueltos y testeados; aquí solo viven las reglas de la fuente.
- **Columnas por rótulo, no por posición** (acceptance): las columnas de partido cambian entre años (2023 no tiene SALF/Aliança.cat; 2026 añade Adelante Andalucía); el test lo verifica con un orden distinto.
- **Corte jerárquico de secciones**: el cuerpo termina en el encabezado de nivel igual o superior; con un corte «a cualquier encabezado» el cuerpo de `Voting intention estimates` quedaría vacío y no se parsearía ninguna tabla.
- **`–`/sin valores no producen resultado**: evita `poll_result` nulas y encaja con la validación de la feature 9 («≥2 partidos con valor»); `len(row.results)` es ese contador.
- **`source` literal + `pollster_name` extraído**: el literal completo queda en `poll.source` y la firma (antes de `(` o `/`) en `pollster`; las reestimaciones del CIS son filas propias, no un caso especial.
- **`ELECTION_TYPE` en el adaptador**: el ámbito (nacional, Congreso) es de la fuente; la carga (feature 9) no lo hardcodea.
- **Año desde la subsección**: las celdas del snapshot real no llevan año; los rangos que cruzan año restan uno al inicio.
- **Warning y seguir**: toda deriva del formato degrada a warning + valor nulo/salto, nunca a excepción; las fixtures fijan las formas actuales.
- **Sin logs INFO**: consistente con el resto de parsers del repo.

## Alternativas descartadas

1. **Parsear por posición** (PP = columna 4, …): prohibido por el acceptance y frágil — las columnas cambian entre años y la wiki añade partidos.
2. **Re-implementar el lexer de tablas en el adaptador**: duplicaría la feature 7 (rowspan, limpieza) y dos fuentes de verdad para el mismo formato.
3. **Trocear por cualquier encabezado o buscar `{|…|}` en toda la página y filtrar por `class`**: las tablas de otras secciones comparten clases (`wikitable collapsible …`); el corte jerárquico por encabezados es simple, explícito y verificado con el señuelo.
4. **Emitir resultados con nulos para `–`/`?`**: ruido en `poll_result`; la ausencia de fila expresa «no listado»/«desconocido» y simplifica la validación de la carga.
5. **Exponer el `Table` del lexer como contrato**: acoplaría la feature 9 al lexer; el contrato es `PollRow` (dataclasses propias).
6. **Dejar el mapeo de partidos para la carga**: es regla de la fuente (rótulo de cabecera → slug) y las fixtures del adaptador deben fijarla; la carga solo hace `get-or-create` con slug/nombre.
7. **`pollster` = literal completo (`CIS (Target Point)`)**: la firma (`CIS`) va a `pollster` y el literal a `source`; el gráfico puede filtrar por `source`.
8. **Parsear HTML o usar una librería**: descartado (wikitexto es el formato canónico; sin dependencias nuevas).
9. **Soporte de `||`/`!!`/celdas multilínea o tablas anidadas**: no existen en la fuente (verificado: 0); se añadirían si una deriva los introduce (warning y a seguir).

## Interfaz para la feature 9

La carga importará `ELECTION_TYPE`, `PARTY_COLUMNS` y `parse_polls` de `ingestor.polls.adapters.wikipedia_polls`; el `revision_id` no lo produce el adaptador (viene del nombre del snapshot). Para el slug del pollster puede reutilizar `slugify` de `elections/loaders/election.py`. `PARTY_COLUMNS` da el nombre legible de los partidos que falten por crear (`salf`, `alianca-cat`).

## Documentación (texto pretendido)

`ingestor/AGENTS.md`, bullet de `src/ingestor/polls/` (R29): se añade al final de la frase existente: «y `wikipedia_polls.py`, reglas de la fuente de sondeos (Wikipedia en inglés: secciones y tablas por año, cabecera, partidos)». El test de docs comprueba las subcadenas `wikipedia_polls.py` y `sondeos`, no el texto completo.
