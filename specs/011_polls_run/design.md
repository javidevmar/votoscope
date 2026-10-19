# Diseño — `polls_run`

Feature 11. Ejecución real y cotejo: corre el ciclo contra la página, cuenta la completitud y documenta la fuente (`.agents/data-sources.md`: formato, rarezas y licencia CC BY-SA con enlace a la revisión). Interfaz de entrada: [`specs/009_polls_load/design.md`](../009_polls_load/design.md) §«Interfaz para las features 10–11» — el ciclo es `fetch-polls` + `ingest-polls` y el cotejo manual usa `poll.source`/`revision_id` — y [`specs/010_polls_schedule/design.md`](../010_polls_schedule/design.md) §«Interfaz para la feature 11».

Esta feature **no añade código de producción**: ejecuta los comandos existentes (features 6 y 9) y produce documentos (informe de ejecución y sección de la fuente) más los tests que fijan los documentos. El estado real de la carga local es **evidencia operativa** (comandos y SQL reproducible en el informe y en `progress/impl_polls_run.md`), sin tests de estado. **No toca el modelo de datos** (sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic; la regla de oro no aplica). Sin dependencias nuevas. Sin excepciones nuevas. No se toca `ingestor/src/` ni `docs/ingestor/ingesta.md` ni `ingestor/AGENTS.md` (no hay cambios de CLI ni de comportamiento que documentar).

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `docs/ingestor/polls-run.md` — informe de la ejecución real y cotejo (R7–R11) |
| modificar | `.agents/data-sources.md` — sección «Sondeos (Wikipedia)» tras «Gazetteer INE» (R12–R15) |
| crear | `ingestor/tests/test_polls_run.py` — tests de documentos (R7–R15) |
| crear | `progress/impl_polls_run.md` — evidencia de la ejecución y trazabilidad R ↔ test (convención del arnés; no es un artefacto del acceptance) |

## La ejecución (T2)

Desde `ingestor/`, contra el Postgres local:

```sh
uv run ingestor fetch-polls      # resuelve la revisión vigente; sin novedades = 1 llamada a la API y exit 0
uv run ingestor ingest-polls     # registra el snapshot pendiente en bronce y carga silver; exit 0
```

- El informe cita el snapshot que quede en disco (el más reciente): `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext`.
- Si `fetch-polls` falla (red, página ausente) o `ingest-polls` falla: parar y documentar (`blocked`); no se parchea código en esta feature.
- La salida de ambos comandos (resumen y exit codes) y los avisos del adaptador se transcriben al informe.

### Estado observado al redactar (2026-10-17)

Contexto para el implementer, **no congelado** (la página y el bronce cambian):

- Snapshots en disco: `1380713440.wikitext` (22:06) y `1380777984.wikitext` (23:20); ambos `processed` en `bronze.ingestion` (fuente `wikipedia-en`).
- `silver` refleja el más reciente (`1380777984`): 575 `poll`, 6.125 `poll_result`, 28 `pollster`; sin `election_id` (no hay elección posterior a 2026 en `silver.election`).
- Tablas por año del snapshot: `2026 (after FA)` (2 filas, solo cabeceras), `2026 (before FA)` (160), `2025` (180), `2024` (171), `2023` (76).
- Completitud observada: declaradas 589 = cargadas 575 + saltadas 14 (10 cabeceras —2 por tabla—, 2 separadoras y 2 resultados: generales 2023 y europeas 2024); frente a la referencia de ≈584 filas declaradas, +5 (la página partió 2026 en dos tablas y añadió filas).
- Avisos del adaptador (los dos únicos): `unknown party column: FA` y `unparseable turnout: 66–67` (→ `turnout` nulo).

## El informe — `docs/ingestor/polls-run.md` (R7–R11)

Estructura fija (los tests de documentos comprueban las subcadenas marcadas):

````markdown
# Ejecución real y cotejo de los sondeos

- Feature 11 (`polls_run`), rama `feature/polls-run`, fecha {fecha}.
- Página: «Opinion polling for the 2026 Spanish general election» — revisión
  [{revid}](https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid={revid}).
- Snapshot: `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext` (sha256 …).

## Comandos ejecutados

```sh
cd ingestor
uv run ingestor fetch-polls     # exit 0 — …
uv run ingestor ingest-polls    # exit 0 — …
```

## Completitud

Método: declaradas = filas `|-` de cada tabla por año (incluye las dos filas de
cabecera); cargadas = `silver.poll` con `revision_id = {revid}`.

| Tabla (año) | Declaradas | Cargadas | Saltadas |
| --- | --- | --- | --- |
| 2026 (after FA) | 2 | 0 | 2 cabeceras |
| … | … | … | … |
| **Total** | {declaradas} | {cargadas} | {saltadas} |

Aritmética: declaradas = cargadas + saltadas. Frente a la referencia de
≈584 filas declaradas: {diferencia y explicación}.

## Método (reproducible)

```sql
select count(*) from silver.poll where revision_id = {revid};
select count(*) from silver.poll_result;
select count(*) from bronze.ingestion where source = 'wikipedia-en' and status = 'processed';
```

## Fuera de alcance

- Columna `Lead` (derivable); tablas de *Voting preferences*, *Victory
  likelihood*, *Hypothetical scenarios* y subnacionales; columnas de partido sin
  filas de datos en las tablas del alcance (p. ej. `FA`).

## Avisos observados

- `unknown party column: FA` — …
- `unparseable turnout: 66–67` — …

## Cotejo

Muestra de {n} sondeos contra el wikitexto de la revisión (firma, fechas, % y
escaños); cada fila compara página → `silver`:

| Firma (source) | Fechas | Comprobación (página → silver) | Veredicto |
| --- | --- | --- | --- |
| … | … | PP 32.6 % / 141 escaños → … | OK |
````

Subcadenas que fija `test_docs_polls_run_completeness` (R7–R10): `fetch-polls`, `ingest-polls`, `Completitud`, `584`, `cabecera`, `separadora`, `resultado`, `Lead`, `Fuera de alcance`, `FA`, `66–67` (el guion es U+2013, el literal del aviso), `select count(*)`, `silver.poll`, `silver.poll_result`, `bronze.ingestion`, `revision_id`, `oldid=`.

`test_docs_polls_run_cotejo` (R11): tras la cabecera `Cotejo`, una tabla markdown con ≥5 filas de datos; cada fila contiene `%` y `escañ`.

## La sección — `.agents/data-sources.md` (R12–R15)

Nueva sección `## Sondeos (Wikipedia)` tras «Gazetteer INE» y antes de «Diferencias observadas entre procesos»:

````markdown
## Sondeos (Wikipedia)

`https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Spanish_general_election`
— encuestas de intención de voto al Congreso desde las generales del 23-jul-2023.
Alcance: la sección *Voting intention estimates* (tablas por año, ámbito nacional).

- **Snapshot (bronce)**: wikitexto de una revisión fija
  (`data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext`), descargado por
  `uv run ingestor fetch-polls` (API, `oldid`) y cargado por
  `uv run ingestor ingest-polls` en `pollster`/`poll`/`poll_result`
  (`bronze.ingestion`, fuente `wikipedia-en`).
- **Formato**: tablas de wikitexto; cabecera a dos filas; cuatro columnas fijas
  (firma, fechas, muestra, participación) + columnas de partido + `Lead`;
  celdas de partido con `%` y proyección de escaños.
- **Rarezas**: …
- **Licencia**: CC BY-SA; citar la fuente y la revisión (`oldid=…`).
- **Verificación**: informe `docs/ingestor/polls-run.md`.
````

Subcadenas de `test_docs_data_sources` (R12, R15): `Sondeos (Wikipedia)`, `Opinion polling for the 2026 Spanish general election`, `wikitext`, `{revid}.wikitext`, `data/raw/polls/wikipedia-en/2026-general/`, `fetch-polls`, `ingest-polls`, `polls-run.md`, `CC BY-SA`, `oldid=`.

Subcadenas de `test_docs_data_sources_quirks` (R13, R14): `rowspan`, `CIS`, `cabecera`, `2026 (after FA)`, `separador`, `resultado`, `Lead`, `cruce de año`, `<2.0`, `fecha de publicación`, `participación`.

Contenido de «Rarezas» (el texto exacto lo redacta el implementer; debe cubrir): `rowspan` y reestimaciones del CIS; tablas por año que pueden partirse (`2026 (after FA)`/`2026 (before FA)`); filas separadoras y de resultado (`#EFEFEF`); `Lead` ignorada; fechas con cruce de año y fecha de publicación como aproximación; `?`/`–`/`<2.0`; participación no numérica; celdas que son solo notas.

## Tests — `ingestor/tests/test_polls_run.py`

Solo documentos: no leen `data/raw/` ni la base de la aplicación, así que corren siempre (también en CI). El estado real de la carga es evidencia operativa (T2): comandos y SQL reproducible en `docs/ingestor/polls-run.md` y `progress/impl_polls_run.md`.

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_docs_polls_run_completeness` | R7–R10 | subcadenas del informe (lista arriba) |
| `test_docs_polls_run_cotejo` | R11 | tabla de cotejo con ≥5 filas; cada fila con `%` y escaños |
| `test_docs_data_sources` | R12, R15 | subcadenas de la sección (lista arriba) |
| `test_docs_data_sources_quirks` | R13, R14 | subcadenas de rarezas (lista arriba) |

Detalles que fijan el contrato:

- Los tests de documentos no se saltan: el informe y la sección van versionados.
- R1–R7 se verifican con la evidencia operativa de la ejecución, no con SELECTs desde el suite: el conteo por tabla, la aritmética y el método SQL quedan en el informe y en `progress/impl_polls_run.md` (decisión aprobada el 2026-10-19).

## Decisiones

- **El informe vive en `docs/ingestor/polls-run.md`** (durable, junto a `ingesta.md`): el conteo y el cotejo son evidencia de esta ejecución y a la vez método reutilizable (job 2×/día, re-verificaciones); los tests de documentos lo fijan. `progress/impl_polls_run.md` se escribe igual (trazabilidad del harness), pero no es el artefacto del acceptance.
- **Estado real como evidencia operativa**: la ejecución (fetch + ingest) y su conteo quedan transcritos en `docs/ingestor/polls-run.md` y `progress/impl_polls_run.md` con comandos y SQL reproducibles. El suite no lee el `silver`/`bronze` local ni depende de `data/raw/` (decisión aprobada el 2026-10-19).
- **La aritmética de completitud es contrato del informe, no de un test**: declaradas (`poll_tables`), cargadas (`parse_polls`/`silver`) y saltadas (cabeceras, separadoras, resultados) quedan desglosadas y cuadradas en el informe; cualquier revisión futura puede repetir el método SQL documentado.
- **Cotejo como tabla markdown de ≥5 filas** con formato fijo: el test cuenta filas y exige `%`/escaños; el contenido lo valida el reviewer contra el snapshot (los sondeos se eligen entre filas con datos completos).
- **Subcadenas estables en los tests de documentos** (patrón del repo: features 6, 9 y 10): fijan el contrato sin acoplarse al texto completo.
- **Sin tocar código**: si la ejecución destapa un defecto del adaptador/loader, se para y se documenta; la corrección se decide fuera de esta feature.
- **No se congelan revisiones ni cifras**: el informe cita la revisión usada (hoy `1380777984`) y recalcula el conteo; el spec fija método, categorías y umbrales (≈584, ≥5 sondeos, ventana del trabajo de campo).

## Alternativas descartadas

1. **Copiar el snapshot real a `tests/fixtures/`** (646 KB): duplicaría el bronce y no aportaría nada — la verificación es del estado local; el parser y el loader ya tienen fixtures (features 8–9).
2. **Tests de estado contra la base de la aplicación**: leen el `silver` local y se saltan en CI; el usuario aprobó (2026-10-19) sustituirlos por evidencia operativa en el informe y `progress/impl_polls_run.md`.
3. **Congelar los números del informe en los tests** (589/575): la página se edita a diario; el método es lo verificable.
4. **Documentar el conteo solo en `progress/impl_polls_run.md`**: es estado de sesión; el acceptance pide documentación revisable (el informe versionado), y los tests no deben leer `progress/`.
5. **Un script `scripts/verify-polls.py` para el conteo**: un fichero más para lo que ya cubren la aritmética del informe y su método SQL reproducible.
6. **Tests que ejecuten `fetch-polls`/`ingest-polls` por `subprocess`**: red en el suite y mutación de los esquemas reales; la ejecución queda documentada en el informe y los tests solo leen.
7. **Meter los sondeos en `docs/ingestor/ingesta.md`**: mezclaría «cómo funciona» con «de dónde vienen los datos»; el acceptance fija `.agents/data-sources.md`.
8. **Mantener tests de estado anclados al snapshot más reciente**: dependían de `data/raw/` y del `silver` local; retirados el 2026-10-19 a favor de la evidencia operativa.

## Notas

- `.agents/data-sources.md` enlaza el informe; el cierre de la iniciativa decidirá si algo más se pliega.
- El cotejo debe incluir la nota del review de la feature 8: la celda `66–67` de participación degrada a nula (warning) y la columna `FA` solo aparece en la cabecera de `2026 (after FA)` (sin filas de datos en el alcance).
