# Requisitos — `gold_matviews`

Feature 19 de [`feature_list.json`](../../feature_list.json). Sustituye las
cuatro vistas de resultados de `gold` por vistas materializadas con índices,
reescribe `result_by_area` sin el `JOIN ... IS NOT DISTINCT FROM` de
`area_blank` y refresca al final de la ingesta. Las dos vistas de sondeos
siguen siendo vistas.

Fuentes de alcance: los seis criterios de `acceptance` de la feature 19, más
las reglas del repositorio ([`AGENTS.md`](../../AGENTS.md),
[`ingestor/AGENTS.md`](../../ingestor/AGENTS.md)) sobre documentación y
sincronización del modelo. El contrato de pantallas y la semántica de
porcentajes vigentes están en [`docs/db/gold.md`](../../docs/db/gold.md).

## R1

El sistema DEBE calcular los votos en blanco de `gold.result_by_area` en el
mismo CTE de hechos que los votos a candidaturas, sin usar
`JOIN ... IS NOT DISTINCT FROM` ni un CTE `area_blank` separado.

## R2

CUANDO se ejecuta el test de regresión sobre los datos cargados en local,
`gold.result_by_area` DEBE devolver las mismas filas y los mismos valores
(`votes`, `pct`) que la definición anterior a esta feature.

## R3

CUANDO se ejecuta `uv run alembic upgrade head`, el sistema DEBE dejar
`gold.election_summary`, `gold.result_by_area`, `gold.result_by_station` y
`gold.station_turnout` como vistas materializadas.

## R4

Las cuatro vistas materializadas DEBEN tener índices que cubran los filtros
del contrato: elección + nivel + área en `result_by_area`, y elección + mesa y
elección + municipio en `result_by_station` y `station_turnout`.

## R5

Cada vista materializada DEBE tener al menos un índice único que permita
`REFRESH MATERIALIZED VIEW CONCURRENTLY`.

## R6

`gold.poll_flat` y `gold.poll_trend` DEBEN seguir siendo vistas normales, no
vistas materializadas.

## R7

`gold.poll_trend` DEBE conservar su orden contractual
`ORDER BY poll_date, poll_id, party_slug`.

## R8

CUANDO `uv run ingestor ingest <ruta>` termina y al menos un fichero quedó en
estado `processed`, el sistema DEBE refrescar las cuatro vistas materializadas
exactamente una vez, al final de la ejecución y fuera del bucle de elecciones.

## R9

SI todos los ficheros de una ejecución de `ingest` se saltaron (`skipped`)
ENTONCES el sistema NO DEBE refrescar ninguna vista materializada.

## R10

CUANDO se ejecuta `uv run ingestor refresh-gold`, el sistema DEBE refrescar
las cuatro vistas materializadas.

## R11

CUANDO se ejecuta `uv run ingestor refresh-gold`, el sistema DEBE salir con
código 0.

## R12

CUANDO se ejecuta `uv run ingestor refresh-gold` dos veces seguidas con los
mismos datos, el sistema DEBE dejar el mismo contenido en las cuatro vistas
materializadas.

## R13

CUANDO se ejecuta `uv run ingestor refresh-gold --concurrently`, el sistema
DEBE refrescar cada vista materializada con
`REFRESH MATERIALIZED VIEW CONCURRENTLY`.

## R14

CUANDO se ejecuta `uv run ingestor refresh-gold --concurrently`, el sistema
DEBE salir con código 0.

## R15

El comando `uv run ingestor ingest-polls` NO DEBE refrescar ninguna vista
materializada.

## R16

`models.py` DEBE declarar las cuatro relaciones de resultados de `gold` con
`info={"matview": True}` y las dos de sondeos con `info={"view": True}`,
conservando las columnas y tipos del contrato.

## R17

CUANDO se ejecuta `uv run alembic check` después de `alembic upgrade head`, el
sistema NO DEBE detectar drift entre `models.py` y la base de datos.

## R18

La página Gold de `docs/db/schema.drawio` DEBE reflejar qué relaciones de
`gold` son vistas materializadas y los índices que las acompañan.

## R19

`.agents/data-model.md`, `.agents/architecture.md` y `docs/db/gold.md` DEBEN
documentar las cuatro vistas materializadas, sus índices y el refresco
(`ingest` y `refresh-gold`) en el mismo commit que el código.

## R20

`docs/ingestor/ingesta.md`, `ingestor/AGENTS.md` y `.agents/status.md` DEBEN
actualizarse con el comportamiento nuevo (comando `refresh-gold`, refresco al
final de `ingest`, migración y relación de vistas), por la regla de
documentación del repositorio.

## R21

Los tests DEBEN crear las cuatro vistas materializadas y sus índices en los
esquemas de test, nunca en el esquema `gold` real.

## R22

Los tests DEBEN validar que las columnas y tipos de las cuatro vistas
materializadas coinciden con `models.py`.

## R23

Los tests DEBEN comprobar, tras un refresco normal de las vistas
materializadas, que los datos nuevos aparecen.

## R24

Los tests DEBEN comprobar, tras un refresco con `--concurrently`, que los
datos nuevos aparecen.

## R25

El rol `votoscope_web` DEBE conservar `SELECT` sobre las cuatro vistas
materializadas y las dos vistas.

## R26

El rol `votoscope_web` NO DEBE tener permisos de escritura ni de creación
sobre `gold`.

## R27

CUANDO se ejecutan en caliente las consultas de resultados del contrato sobre
los datos de local, el sistema DEBE responder en menos de 50 ms por consulta.

## Decisiones de interpretación

1. **«Migración autogenerada»**: Alembic no autogenera vistas materializadas
   ni sus índices. La revisión se crea con `alembic revision` y su DDL sale de
   `gold.py`, como ya hace `bcd8a7409aec`; `alembic check` (R17) es la garantía
   de que no hay drift. Ver `design.md` §«Migración».
2. **Refresco con ejecuciones mixtas**: si en una misma ejecución de `ingest`
   hay elecciones `processed` y elecciones `failed`, se refresca una vez
   (hay ficheros procesados) y el proceso sale con código 1 por los fallos. R8
   y R9 solo distinguen «algún processed» de «ningún processed».
3. **Test de regresión «sobre los datos de local»**: se materializa como un
   test live que compara la vista materializada con la definición anterior
   (SQL legacy como oráculo) sobre la base local, y se salta si no hay datos;
   además hay un test determinista con el fixture sembrado para CI.
4. **«Menos de 50 ms en caliente»**: test live con `EXPLAIN (ANALYZE, FORMAT
   JSON)`, una ejecución de calentamiento y la mejor de tres; se salta sin base
   o sin datos de elecciones. La medición manual se documenta en
   `progress/impl_gold_matviews.md`.
5. **`votoscope_web` conserva SELECT**: se concede explícitamente en la
   migración (además de los privilegios por defecto ya existentes) y los tests
   del rol pasan a inspeccionar también `relkind = 'm'`.
6. **Vistas materializadas pobladas en la migración**: se crean `WITH DATA`
   (comportamiento por defecto) para que la web funcione justo después de
   `alembic upgrade head`; el refresco posterior es idempotente.

## Trazabilidad `acceptance` ↔ `R<n>`

| # | Criterio de `acceptance` (resumen) | Requisitos |
| --- | --- | --- |
| 1 | `result_by_area` reescrita sin `JOIN ... IS NOT DISTINCT FROM`, blancos en el mismo CTE, mismos valores con test de regresión local | R1, R2 |
| 2 | Cuatro vistas materializadas con índices; `poll_flat`/`poll_trend` siguen siendo vistas | R3, R4, R5, R6, R7 |
| 3 | Refresco una vez al final de `ingest` si hubo ficheros procesados; `refresh-gold [--concurrently]`; `ingest-polls` no refresca | R8, R9, R10, R11, R12, R13, R14, R15 |
| 4 | `models.py` con `info` de matview, `alembic check` sin drift, ERD y docs actualizados | R16, R17, R18, R19 (R20 por regla del repo) |
| 5 | `test_gold.py` crea matviews en esquemas de test, valida columnas y ejercita el refresco; `votoscope_web` conserva SELECT | R21, R22, R23, R24, R25, R26 |
| 6 | Consultas del contrato de resultados por debajo de 50 ms en caliente en local | R27 |
