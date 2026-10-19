# Implementación — `polls_run` (feature 11)

- Rama: `feature/polls-run` (stack de `polls-wikipedia` sobre `feature/polls-schedule`).
- Fecha: 2026-10-18.
- Spec: `specs/011_polls_run/` (T1–T7, requirements R1–R15).
- Sin cambios de modelo, sin código de producción nuevo, sin dependencias nuevas.

## Cambio de criterio (2026-10-19)

- Aprobado por el usuario: se retiran los tests de estado
  (`test_snapshot_present_and_registered_processed`,
  `test_silver_matches_snapshot_parse`, `test_silver_covers_year_tables_and_range`,
  `test_completeness_arithmetic_no_lost_rows`) y los helpers `_newest_snapshot` /
  `_real_session`. Motivo: leían el `silver` y el `data/raw/` locales; el estado
  real pasa a **evidencia operativa** (informe y este documento).
- La infraestructura de tests (`ingestor/tests/conftest.py`) deja de usar
  esquemas dentro de la BD configurada: crea una **base de datos temporal por
  sesión** (`votoscope_test_<pid>`) desde la BD de mantenimiento `postgres` y la
  borra al terminar. El suite ya no depende de que exista la BD de la aplicación.

## Evidencia de la ejecución real (T2)

Página: «Opinion polling for the 2026 Spanish general election».
Revisión usada: **1380859635**, `timestamp=2026-10-18T11:36:42Z`.
Snapshot: `data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext`
(651.942 bytes; sha256 `8a21b27fd3ec6c05bd2766ef3ef98a8f2f3780378b43b0a83d066b43b18f50c2`).

Comandos desde `ingestor/`:

```sh
uv run ingestor fetch-polls      # exit 0 — revid=1380859635, snapshot descargado
uv run ingestor ingest-polls     # exit 0 — revision 1380859635 processed (575 polls)
```

- `fetch-polls` resolvió la revisión con una llamada a la API y descargó el
  snapshot (no existía en disco).
- `ingest-polls` saltó los dos snapshots previos (`1380713440`, `1380777984`,
  ya `processed`), registró el nuevo en `bronze.ingestion` (`processed`,
  `source=wikipedia-en`, ruta relativa a `RAW_DIR`, sha256) y reemplazó
  `poll`/`poll_result` con el snapshot nuevo.
- Estado final en `silver`: **575 `poll`** (`revision_id=1380859635`),
  **6.125 `poll_result`**, **28 `pollster`**.
- Anualidades del trabajo de campo (`fieldwork_end`): 2023=71, 2024=168,
  2025=178, 2026=158. `min(fieldwork_start)=2023-07-24`,
  `max(fieldwork_end)=2026-10-11`.

### Completitud (método del informe)

| Tabla (año) | Declaradas | Cargadas | Saltadas |
| --- | --- | --- | --- |
| 2026 (after FA) | 2 | 0 | 2 cabeceras |
| 2026 (before FA) | 160 | 158 | 2 cabeceras |
| 2025 | 180 | 178 | 2 cabeceras |
| 2024 | 171 | 168 | 2 cabeceras + 1 resultado |
| 2023 | 76 | 71 | 2 cabeceras + 2 separadoras + 1 resultado |
| **Total** | **589** | **575** | **14** |

Aritmética: 589 = 575 + 14. Frente a ≈584 del plan: +5, explicado por la
partición de 2026 (`2026 (after FA)` + `2026 (before FA)` = 162 declaradas;
las otras tres anualidades siguen 180/171/76).

### Avisos del adaptador observados

- `unknown party column: FA` — columna de la cabecera de `2026 (after FA)`;
  sin filas de datos → ningún `poll_result`.
- `unknown party column: FV` — columna nueva de esta revisión (no estaba en la
  anterior), en la misma cabecera; sin filas de datos → ningún `poll_result`.
- `unparseable turnout: 66–67` — `Ipsos/La Vanguardia`, 15–21 May 2025,
  muestra 2.000 → `turnout` nulo; el resto de la fila se carga.

No se destapó ningún defecto del adaptador ni del loader: los tres avisos son
el comportamiento previsto ante deriva/novedades de la fuente. No aplica
`blocked`.

## Documentos

- `docs/ingestor/polls-run.md` — informe de ejecución, completitud, método SQL,
  fuera de alcance, avisos y cotejo de 6 sondeos.
- `.agents/data-sources.md` — sección «Sondeos (Wikipedia)» (formato, rarezas
  estructurales y de valores, licencia CC BY-SA y enlace `oldid`).
- `ingestor/tests/test_polls_run.py` — tests de documentos (informe y sección
  de la fuente).

## Verificación

- `cd ingestor && uv run pytest -q` → **136 passed**.
- `uv run pytest tests/test_polls_run.py -q` → **4 passed** (solo documentos).
- `DATABASE_URL=postgresql+psycopg://votoscope:votoscope@localhost:5434/does_not_exist uv run pytest -q` → **136 passed**: el fixture crea su BD temporal y no necesita que exista la BD configurada.
- `docker compose exec -T db psql -U votoscope -d votoscope -c "\l"` → sin bases `votoscope_test_*` tras el suite (el teardown las borra).
- `uv run ruff check .` → limpio.
- `uv run ruff format --check .` → limpio.
- `uv run alembic check` (dentro de `./init.sh`) → sin drift.
- `./init.sh` → **exit 0** (puerta verde): tras cerrar la #10 solo queda la #11
  en `in_progress`; pasos 4–5 verdes (ruff, **136 passed**, `alembic check` sin
  drift). T7 cerrada con esta evidencia.

### Cambios del review aplicados

- Enlace de `.agents/data-sources.md` a `../docs/ingestor/polls-run.md`
  (antes `../../…`, resolvía fuera del repo); `test_docs_data_sources` ahora
  exige esa subcadena para no dar por buena una referencia rota.
- T7 reabierta (`[ ]`) mientras la puerta estaba roja por las dos
  `in_progress`; cerrada (`[x]`) al quedar `./init.sh` en verde tras el cierre
  de la #10.

## Trazabilidad R ↔ test

R1–R7 se verifican con **evidencia operativa** (comandos y SQL reproducible en
`docs/ingestor/polls-run.md` y en este documento), no con tests de estado
(decisión aprobada el 2026-10-19).

| Requirement | Evidencia / test |
| --- | --- |
| R1 | Evidencia operativa — `fetch-polls` exit 0; revisión `1380859635` y ruta `data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext` en el informe y en este impl |
| R2 | Evidencia operativa — `ingest-polls` exit 0; snapshot registrado `processed` en `bronze.ingestion` (`source=wikipedia-en`, sha256, `file_path` relativo a `RAW_DIR`) |
| R3 | Evidencia operativa — 575 `silver.poll` con `revision_id=1380859635`, igual a las filas parseadas del snapshot |
| R4 | Evidencia operativa — 6.125 `silver.poll_result` del snapshot |
| R5 | Evidencia operativa — anualidades del trabajo de campo: 2023=71, 2024=168, 2025=178, 2026=158 |
| R6 | Evidencia operativa — `min(fieldwork_start)=2023-07-24` (dentro de 23-jul / 31-ago-2023) |
| R7 | Evidencia operativa — tabla de completitud 589 = 575 + 14 y método SQL en el informe; `test_docs_polls_run_completeness` fija las subcadenas (`Completitud`, `584`, `cabecera`, `separadora`, `resultado`) |
| R8 | `test_docs_polls_run_completeness` (`fetch-polls`, `ingest-polls`, `select count(*)`, `silver.poll`, `silver.poll_result`, `bronze.ingestion`, `revision_id`, `oldid=`) |
| R9 | `test_docs_polls_run_completeness` (`Lead`, `Fuera de alcance`, `FA`) |
| R10 | `test_docs_polls_run_completeness` (`FA`, `66–67`; el informe añade `FV`) |
| R11 | `test_docs_polls_run_cotejo` — ≥5 filas de tabla tras `## Cotejo`, cada una con `%` y `escañ` (el informe trae 6) |
| R12 | `test_docs_data_sources` (`Sondeos (Wikipedia)`, título, `wikitext`, `{revid}.wikitext`, ruta, `fetch-polls`, `ingest-polls`, `polls-run.md` y el enlace `../docs/ingestor/polls-run.md`; además descarta el enlace roto `../../docs/ingestor/polls-run.md`) |
| R13 | `test_docs_data_sources_quirks` (`rowspan`, `CIS`, `cabecera`, `2026 (after FA)`, `separador`, `resultado`, `Lead`) |
| R14 | `test_docs_data_sources_quirks` (`cruce de año`, `<2.0`, `fecha de publicación`, `participación`) |
| R15 | `test_docs_data_sources` (`CC BY-SA`, `oldid=`) |

## Tasks

- T1–T7: `[x]` en `specs/011_polls_run/tasks.md`. T7 cerrada con la puerta
  `./init.sh` en verde (exit 0) tras el cierre de la feature 10.
