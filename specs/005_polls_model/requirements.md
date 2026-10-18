# Requisitos — `polls_model`

Feature `id 5` de [`feature_list.json`](../../feature_list.json). Alcance: solo el modelo `silver` de los sondeos y su sincronización ERD ↔ `models.py` ↔ migración. Parser, loader y CLI son features posteriores.

## R1

El sistema DEBE definir la tabla `silver.pollster` con `id` sustitutiva (PK), `name` no nulo y `slug` `String(60)` con restricción única, siguiendo el patrón de `silver.party`.

## R2

El sistema DEBE definir la tabla `silver.poll` con `id` sustitutiva (PK) y `pollster_id` como clave ajena no nula a `silver.pollster.id`.

## R3

El sistema DEBE definir en `silver.poll` las columnas `source` (`Text`) no nula, `election_type` (`String(20)`) no nula y `revision_id` (`BigInteger`) no nula.

## R4

El sistema DEBE declarar `silver.poll.election_id` como clave ajena nullable a `silver.election.id`.

## R5

El sistema DEBE declarar `silver.poll.fieldwork_start` y `silver.poll.fieldwork_end` como `Date` nullables y `silver.poll.sample_size` como entero nullable.

## R6

El sistema DEBE declarar `silver.poll.turnout` como `Numeric(5,2)` nullable con un CHECK que restrinja sus valores al rango 0–100.

## R7

El sistema DEBE definir la tabla `silver.poll_result` con `id` sustitutiva (PK), `poll_id` como clave ajena indexada a `silver.poll.id` y `party_id` como clave ajena indexada a `silver.party.id`.

## R8

El sistema DEBE declarar `silver.poll_result.pct` como `Numeric(5,2)` nullable con un CHECK que restrinja sus valores al rango 0–100.

## R9

El sistema DEBE declarar `silver.poll_result.seats_min` y `silver.poll_result.seats_max` como enteros nullables.

## R10

El sistema DEBE imponer una restricción única sobre (`poll_id`, `party_id`) en `silver.poll_result`.

## R11

CUANDO se aplica la migración de esta feature con `uv run alembic upgrade head` sobre una base en la revisión anterior, el sistema DEBE crear `silver.pollster`, `silver.poll` y `silver.poll_result` con sus columnas, claves ajenas, unicidad y CHECKs.

## R12

CUANDO se ejecuta `uv run alembic check` con la base migrada, el sistema DEBE informar de que no hay operaciones pendientes entre `models.py` y la base (sin drift).

## R13

El sistema DEBE añadir a `docs/db/schema.drawio` la página «Silver polls» con las tablas `pollster`, `poll` y `poll_result` completas y cajas de referencia (atenuadas) de `party` y `election`.

## R14

El sistema DEBE añadir a `docs/db/schema.drawio` la página «Bronze polls» con el flujo del snapshot `.wikitext` de `data/raw/polls/` al registro `bronze.ingestion`, con `ingestion` como caja de referencia (atenuada) de la página «Bronze».

## R15

El sistema DEBE actualizar `.agents/data-model.md` con la regla «una página por esquema y dominio (Bronze, Silver, Bronze polls, Silver polls)» y con `pollster`, `poll` y `poll_result` descritas en el modelo v2.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| `silver.pollster` (slug UK) | R1 |
| `silver.poll` (pollster_id FK, source, election_type, election_id nullable, fieldwork_start/end, sample_size, turnout con CHECK 0-100, revision_id) | R2, R3, R4, R5, R6 |
| `silver.poll_result` (poll_id FK, party_id FK, pct CHECK 0-100, seats_min/max, UK(poll_id, party_id)) | R7, R8, R9, R10 |
| migración autogenerada aplicada y `alembic check` sin drift | R11, R12 |
| `docs/db/schema.drawio`: páginas nuevas *Bronze polls* y *Silver polls* (party y election como cajas atenuadas) | R13, R14 |
| `.agents/data-model.md` actualizado: «una página por esquema y dominio» | R15 |

## Nota de verificación

- R1–R10: tests de metadata (sin base de datos) en `ingestor/tests/test_polls_model.py`.
- R11–R12: se verifican con `uv run alembic upgrade head` + `uv run alembic check` (pasos ya presentes en la CI del ingestador y en `init.sh` §5, con el Postgres de `:5434`). No se duplican en pytest: la base de datos es el propio objeto de verificación.
- R13–R15: tests que parsean `docs/db/schema.drawio` (XML, biblioteca estándar) y `.agents/data-model.md` desde `ingestor/tests/test_polls_model.py`.
