# Requisitos — `polls_run`

Feature `id 11` de [`feature_list.json`](../../feature_list.json); tarea 7 del plan [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md) (§«Tareas»: ejecución real con conteo de completitud, cotejo de una muestra y sección «Sondeos (Wikipedia)» en `data-sources.md`). Alcance: ejecutar el ciclo `uv run ingestor fetch-polls` + `uv run ingestor ingest-polls` sobre el Postgres local contra la página real, verificar la carga (completitud y cotejo) y documentar la fuente (formato, rarezas y licencia) en `.agents/data-sources.md`. Los comandos son los de las features 6 y 9 —interfaz fijada en [`specs/009_polls_load/design.md`](../009_polls_load/design.md) §«Interfaz para las features 10–11»—; esta feature **no añade código de aplicación**: sus artefactos son el informe de ejecución, la sección de la fuente y los tests que fijan el estado cargado y los documentos.

Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Sin dependencias nuevas. Sin excepciones nuevas.

El spec fija **el método y los umbrales**, no valores congelados: la página se edita a diario (filas nuevas, revisiones nuevas), así que el informe cita la revisión realmente usada y el conteo se recalcula en cada ejecución.

## R1

CUANDO se ejecuta `uv run ingestor fetch-polls`, el sistema DEBE dejar en `data/raw/polls/wikipedia-en/2026-general/` el fichero `{revision_id}.wikitext` de la revisión vigente de la página de sondeos.

## R2

CUANDO `uv run ingestor ingest-polls` procesa ese snapshot, el sistema DEBE registrarlo `processed` en `bronze.ingestion` con fuente `wikipedia-en`, su sha256 y su ruta relativa a `RAW_DIR`.

## R3

CUANDO carga ese snapshot, el sistema DEBE dejar en `silver` una fila de `poll` por cada fila de datos del snapshot, con el `revision_id` del fichero.

## R4

CUANDO carga ese snapshot, el sistema DEBE dejar en `silver` una fila de `poll_result` por cada resultado del snapshot.

## R5

El sistema DEBE cargar sondeos de las cuatro anualidades del alcance (2023, 2024, 2025 y 2026), con al menos un sondeo con `fieldwork_end` en cada año.

## R6

El sondeo más antiguo de la carga DEBE tener su trabajo de campo no anterior al 23-jul-2023 (fecha de las generales) ni posterior al 31-ago-2023.

## R7

El informe `docs/ingestor/polls-run.md` DEBE documentar el conteo de completitud del snapshot usado —filas declaradas por tabla de año y total, sondeos cargados en `silver` y filas saltadas por diseño (cabeceras, separadoras y resultados)— comparado con la referencia ≈584 del plan y con la diferencia explicada.

## R8

El informe DEBE incluir el método reproducible del conteo: los comandos ejecutados y las consultas SQL sobre `silver.poll`, `silver.poll_result` y `bronze.ingestion`, con el `revision_id` y el enlace (`oldid`) a la revisión de la página.

## R9

El informe DEBE identificar los elementos fuera de alcance que el conteo no incluye: la columna `Lead`, las tablas de secciones distintas de *Voting intention estimates* y las columnas de partido sin filas de datos en las tablas del alcance (p. ej. `FA`).

## R10

El informe DEBE documentar los avisos del adaptador observados en la ejecución y su efecto (la columna `FA` desconocida y la participación `66–67` cargada como nula).

## R11

El informe DEBE documentar el cotejo manual de al menos cinco sondeos contra la página —firma, fechas, porcentajes y escaños de al menos dos partidos por sondeo— con el resultado de cada comprobación.

## R12

`.agents/data-sources.md` DEBE incluir una sección «Sondeos (Wikipedia)» con el formato del wikitexto y el contrato del snapshot —revisión fija, `{revid}.wikitext` bajo `data/raw/polls/wikipedia-en/2026-general/`, comandos `fetch-polls`/`ingest-polls`, carga en `pollster`/`poll`/`poll_result`— y la referencia al informe de ejecución.

## R13

La sección DEBE documentar las rarezas estructurales de la fuente: `rowspan` y reestimaciones del CIS, cabecera a dos filas, tablas por año que pueden partirse (p. ej. `2026 (after FA)`), filas separadoras y de resultado, y la columna `Lead` ignorada.

## R14

La sección DEBE documentar las rarezas de los valores: fechas (rangos, cruce de año y fecha de publicación como aproximación), `<2.0`, `?`/`–`, participación no numérica y celdas que son solo notas.

## R15

La sección DEBE declarar la licencia CC BY-SA del texto de Wikipedia y enlazar la revisión usada (`oldid`).

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «`fetch-polls` + `ingest-polls` ejecutados en local sobre la página de 2026; silver cargado con todas las encuestas de la página (las cuatro tablas, desde las generales del 23-jul-2023)» | R1, R2, R3, R4, R5, R6 |
| «conteo de completitud documentado: sondeos cargados vs filas declaradas por la página (≈584), con las filas saltadas por diseño identificadas (separadoras, resultado de 2023, columnas fuera de alcance)» | R7, R8, R9 |
| «cotejo de un puñado de filas contra la página (firma, fechas, % y escaños) documentado» | R11 |
| «sección «Sondeos (Wikipedia)» en `.agents/data-sources.md` con formato, rarezas y licencia CC BY-SA» | R12, R13, R14, R15 |
| Extra: avisos conocidos de la ejecución (columna `FA`; participación `66–67`) | R10 |

## Notas de alcance

- **Ejecución y documentación, no código**: si la ejecución real destapa un defecto del adaptador o del loader, se para y se documenta (`blocked`); la corrección se decide fuera de esta feature.
- **La página es cambiante**: no se congelan revisiones ni recuentos. «Las cuatro tablas» del acceptance son las cuatro anualidades de *Voting intention estimates* (2023–2026); una anualidad puede partirse en varias tablas (hoy, `2026 (after FA)` y `2026 (before FA)`).
- **Filas declaradas**: filas `|-` de cada tabla por año, incluidas las dos filas de cabecera, las separadoras y las de resultado. El desglose de saltadas (cabeceras, separadoras, resultados —el de las generales de 2023 y el de las europeas de 2024—) y la aritmética `declaradas = cargadas + saltadas` son el contrato del informe; las cifras concretas las recalcula cada ejecución.
- **Cotejo manual**: contra el wikitexto de la revisión usada; el informe deja la muestra por escrito con el enlace a la revisión.
- **Los tests de ejecución real son de solo lectura** (SELECT) y se saltan sin Postgres o sin snapshot: `data/raw/` es local y no se versiona, así que la CI queda verde sin ellos; en local verifican el estado cargado.
- **Sin cambios de modelo**: esta feature no toca `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica).

## Nota de verificación

- R1–R6: `ingestor/tests/test_polls_run.py` — `test_snapshot_present_and_registered_processed` (R1, R2), `test_silver_matches_snapshot_parse` (R3, R4) y `test_silver_covers_year_tables_and_range` (R5, R6); anclados al snapshot más reciente de `RAW_DIR/polls/wikipedia-en/2026-general/` y a SELECTs sobre el Postgres local, con `pytest.skip` si no hay snapshot o base.
- R7: `test_completeness_arithmetic_no_lost_rows` (aritmética sobre el snapshot real: declaradas = cargadas + saltadas, y cargadas de `silver` = parseadas) y `test_docs_polls_run_completeness` (subcadenas del informe).
- R8–R10: `test_docs_polls_run_completeness` (subcadenas del informe).
- R11: `test_docs_polls_run_cotejo` (tabla de cotejo con ≥5 filas, con `%` y escaños por fila).
- R12–R15: `test_docs_data_sources` (R12, R15) y `test_docs_data_sources_quirks` (R13, R14).
