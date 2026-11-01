# Requisitos — `source_norm`

Feature `id 18` de [`feature_list.json`](../../feature_list.json) (iniciativa `polls-wikipedia`). Alcance: separar los papeles del **literal de la firma** de los sondeos de Wikipedia —encuestadora, medio y reestimador— en el adaptador (feature 8) y representar la distinción en `silver` (dos columnas nuevas en `poll`, feature 5), con carga idempotente en el loader (feature 9) y documentación al día.

Contexto verificado al redactar (base local, 2026-10-18; inventario en [`design.md`](design.md) §«Inventario de literales reales»): `silver.poll` tiene 575 filas y 43 literales de firma distintos en el último snapshot; los tres snapshots locales (`1380713440`, `1380777984`, `1380859635`) dan la misma unión de 43. El inventario de la feature se construye sobre **todo el bronce disponible** (`data/raw/polls/**`), no solo el último fetch: los literales que solo aparezcan en revisiones anteriores (o en futuras) entran en la tabla de casos; la lista no es cerrada. Tres formas:

- `Encuestadora/Medio`: `SocioMétrica/El Español`, `Target Point/El Debate`, `ODEC/Mediaflows–UV`… (el segundo tramo es el medio/comisionante; se guarda su literal).
- `CIS {{smaller|(Reestimador)}}`: `CIS (Target Point)`, `CIS (Ateneo del Dato)`, `CIS (Logoslab)`, `CIS (Sondaxe)`, `CIS (Demócrata)`, `CIS (Opina 360)`, `CIS (SocioMétrica)`, `CIS (Jaime Miquel)`, `CIS (JM)` — proyección alternativa sobre los datos brutos del CIS; **solo el CIS** usa el paréntesis.
- Sin separadores: `CIS`, `More in Common`, `Ateneo del Dato`, `PSOE`, `Sumar` — solo encuestadora conocida.

Orden: esta feature llega **después** de las 13/14 (encoladas) y no toca la resolución de partidos; trabajará sobre el adaptador ya sin `PARTY_COLUMNS` y el loader con `PartyResolver` (ver [`design.md`](design.md) §«Orden y convivencia con otras features»).

## R1

CUANDO el literal de la firma contiene una barra (`Encuestadora/Medio`), el sistema DEBE emitir como `pollster_name` el texto anterior a la primera barra y como `media` el texto posterior, ambos sin espacios sobrantes (`SocioMétrica/El Español` → `SocioMétrica` + `El Español`).

## R2

CUANDO el literal de la firma termina en un paréntesis (`Encuestadora (Reestimador)`), el sistema DEBE emitir el texto anterior como `pollster_name` y el contenido del paréntesis como `reestimator` (`CIS (Target Point)` → `CIS` + `Target Point`).

## R3

CUANDO el literal de la firma no contiene ni barra ni paréntesis, el sistema DEBE emitir el literal completo (sin espacios sobrantes) como `pollster_name` y NO DEBE inventar `media` ni `reestimator` (ambos nulos).

## R4

CUANDO el literal de la firma contiene a la vez un paréntesis final y una barra, el sistema DEBE extraer primero el reestimador del paréntesis y después, del texto restante, la encuestadora y el medio por la primera barra (descomposición determinista, sin ambigüedad).

## R5

SI un separador deja vacío el medio o el reestimador ENTONCES el sistema DEBE registrar un warning con el literal y DEBE dejar ese papel nulo (la fila no se aborta en el adaptador).

## R6

El sistema DEBE exponer en cada `PollRow` los tres papeles extraídos del literal —`pollster_name`, `media` y `reestimator`—, con `media` y `reestimator` nulos cuando el literal no los distinga.

## R7

El sistema DEBE conservar el literal completo de la firma en `poll.source`, sin normalizarlo (no se pierde información; es la trazabilidad con la página y con la licencia CC BY-SA).

## R8

El sistema DEBE añadir a `silver.poll` las columnas `media` y `reestimator`, de tipo texto y nulables.

## R9

El sistema DEBE declarar `Poll.media` y `Poll.reestimator` en `ingestor/src/ingestor/models.py` y DEBE generar la migración de Alembic con `alembic revision --autogenerate` (nunca DDL a mano, nunca editando una migración ya aplicada).

## R10

CUANDO se ejecutan `uv run alembic upgrade head` y `uv run alembic check` contra la base local, el sistema NO DEBE reportar drift.

## R11

El sistema DEBE reflejar `media` y `reestimator` en la página «Silver polls» de `docs/db/schema.drawio` —una fila de tabla por columna, con su nulabilidad— manteniendo la sincronización ERD ↔ modelos ↔ migración.

## R12

El sistema DEBE actualizar `.agents/data-model.md` (bullet `silver.poll`) con la distinción encuestadora/medio/reestimador del literal de firma.

## R13

CUANDO `ingest-polls` carga un snapshot, el sistema DEBE escribir en `poll.media` y `poll.reestimator` los valores de cada fila del adaptador (`NULL` cuando el literal no los distinga).

## R14

CUANDO se vuelve a cargar el mismo snapshot (`ingest-polls --force`), el sistema DEBE dejar `poll` con el mismo contenido —`media` y `reestimator` incluidos— sin duplicar filas (la recarga es idempotente).

## R15

El sistema DEBE cubrir las reglas de extracción con tests sobre la **unión de literales de todos los snapshots de bronce** (`data/raw/polls/**`), no solo el último fetch: las diez formas del CIS (`CIS` y sus nueve reestimaciones), las formas `Encuestadora/Medio` y los literales sin separadores, recogidos en el test como tabla de casos, sin red, sin `refs/` y sin `data/raw/`. Las revisiones históricas con literales que ya no aparecen en la página actual también entran en la tabla.

## R16

El sistema DEBE cubrir con tests la carga de los dos campos en `poll` y la idempotencia de la recarga (esquemas de test de `conftest.py`) y DEBE actualizar los tests de modelo/ERD y de documentación afectados (`test_polls_model.py`, `test_polls_load.py`, `test_polls_run.py`).

## R17

El sistema DEBE actualizar la sección «Sondeos (Wikipedia)» de `.agents/data-sources.md` con las reglas de los papeles del literal (formas, ejemplos reales, el paréntesis del CIS como proyección alternativa y la ausencia de invención cuando el literal no distingue medio ni reestimador).

## R18

El sistema DEBE actualizar `docs/ingestor/ingesta.md` —el paso 6 de «Comportamiento de `ingest-polls`» y la fila `poll` de «Qué queda en `silver`»— con `media`/`reestimator`, la idempotencia de la recarga y la nota de recarga `--force` para poblar las filas ya cargadas.

## R19

El sistema DEBE actualizar `ingestor/AGENTS.md` (bullet de `src/ingestor/polls/`) con la separación de papeles del literal de firma.

## R20

El sistema NO DEBE usar una lista blanca de encuestadoras, medios o reestimadores: las reglas R1–R4 se aplican a cualquier literal y un literal nuevo se descompone (o se deja con sus papeles nulos) sin descartarse ni corregirse contra una tabla.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «las reglas de extracción distinguen encuestadora, medio y reestimador cuando el literal lo contiene (p. ej. `CIS (Target Point)` → CIS + reestimador Target Point; `SocioMétrica/El Español` → SocioMétrica + medio El Español), sin inventar datos cuando no aplica» | R1, R2, R3, R4, R5, R6, R7 |
| «la distinción queda representada en silver (esquema o derivación documentada como decisión) y la recarga del snapshot la aplica de forma idempotente» | R8, R9, R10, R11, R12, R13, R14 |
| «tests con los literales reales de la página (CIS y sus reestimaciones, medios y encuestadoras solas)» | R15, R16, R20 |
| «`.agents/data-sources.md` y docs del ingestador actualizados» | R17, R18, R19 |
| Extra: decisión de representación (columnas vs derivación) documentada con alternativa descartada | [`design.md`](design.md) §«Decisión» y §«Alternativas descartadas» |
| Extra: regla de oro del modelo de datos (ERD ↔ `models.py` ↔ migración) | R8–R11 |
| Extra: extracción genérica, sin lista blanca de literales | R20 |

## Notas de alcance

- **Solo el literal**: la extracción no consulta ningún catálogo ni inventa identidad (R3); no se fusionan alias (`CIS (JM)` y `CIS (Jaime Miquel)` se guardan tal cual) y `PSOE`/`Sumar` (comisionante sin encuestadora conocida) se quedan como encuestadora literal, como hoy (regla de la feature 8, R21). Una curación de identidades de medio/reestimador queda fuera del alcance.
- **Sin cambio de contrato de `poll.source`**: sigue siendo el literal completo (R7); los consumidores de la feature 11 (cotejo) no se rompen.
- **Sin cambio de `pollster`**: para los literales del inventario (43 en los tres snapshots locales) la encuestadora extraída es la misma que ya produce la regla vigente (`_pollster_name`); la recarga no cambia `pollster_id` de ninguna fila.
- **Sin dependencias nuevas**: `re`, `logging` y `dataclasses` (stdlib); el modelo, Alembic y SQLAlchemy ya están aprobados.
- **Sin cambios en `web/`** ni en la CLI: `ingest-polls` mantiene su interfaz (`[ruta] [--force]`).
- **Documentación operativa**: poblar `media`/`reestimator` en las filas ya cargadas exige recargar el snapshot (`ingest-polls --force`); el cron de la feature 10 lo hace por sí solo pero el guard saltaría un snapshot ya `processed`. Se documenta en `ingesta.md` (R18) y se ejecuta como evidencia de implementación (ver [`design.md`](design.md) §«Evidencia»).

## Nota de verificación

- R1–R7: tests del adaptador en `ingestor/tests/test_wikipedia_polls.py` (`parse_signature` con la tabla del inventario —43 en los tres snapshots locales— + casos sintéticos de combinación, partes vacías y un literal no inventariado que debe descomponerse por las reglas generales; aserciones de `media`/`reestimator` en los recortes reales `real_2026_head.wikitext`).
- R8–R11: tests de modelo/ERD en `ingestor/tests/test_polls_model.py` (metadata de las columnas y columnas esperadas de la página «Silver polls» del drawio) + `uv run alembic check` (R10, verificado por comando como en la feature 5).
- R13–R14: tests de carga en `ingestor/tests/test_polls_load.py` (columnas en `poll` tras la carga y recarga `--force` idempotente) con los esquemas de test.
- R12, R17–R19: tests de documentación que leen los ficheros y comprueban subcadenas estables (`test_polls_model.py`, `test_polls_run.py`, `test_polls_load.py`).
- R15–R16, R20: la propia suite, con fixtures y literales locales (sin red ni `refs/` ni `data/raw/`); la extracción no consulta ninguna tabla de literales conocidos.
