# Diseño — `gold_matviews`

Feature 19 de [`feature_list.json`](../../feature_list.json). Alcance: las
cuatro relaciones de resultados de `gold` pasan a vistas materializadas con
índices, `result_by_area` se reescribe sin el `JOIN ... IS NOT DISTINCT FROM`
de `area_blank`, el refresco corre una vez al final de `ingest` y existe el
comando `refresh-gold [--concurrently]`. Las dos vistas de sondeos no cambian
de naturaleza.

## Estado observado (2026-11-01)

- `head` de Alembic: `0fa48964369e` (`poll_source_roles`). Cadena:
  `2a1c9e836128` → `06a250c36252` → `368c5831061d` → `bcd8a7409aec` (gold) →
  `9f3c2a1b7d40` (rol web) → `0fa48964369e`.
- `ingestor/src/ingestor/gold.py`: `_VIEW_SQL` con las seis vistas y
  `view_ddl(gold_schema, silver_schema)`. `result_by_area` usa un CTE
  `area_blank` y lo une con
  `ab.community_ine_code IS NOT DISTINCT FROM at.community_ine_code` (y las
  columnas de provincia y municipio).
- `ingestor/src/ingestor/models.py` (§`gold`): las seis son `Table` de Core
  con `info={"view": True}`, sin PK/FK ni índices.
- `ingestor/alembic/env.py`: `include_object` excluye del autogenerate las
  tablas con `info["view"]`.
- `ingestor/alembic/versions/bcd8a7409aec_gold_views.py`: crea el esquema y
  ejecuta `view_ddl()`; su `downgrade` hace `DROP VIEW IF EXISTS`.
- `ingestor/alembic/versions/9f3c2a1b7d40_web_readonly_role.py`: crea
  `votoscope_web`, `GRANT SELECT ON ALL TABLES IN SCHEMA gold` y
  `ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES`.
- `ingestor/tests/conftest.py`: crea los esquemas de test, `create_all` de las
  tablas (excluye `info["view"]`) y las seis vistas con `view_ddl()`.
- `ingestor/tests/test_gold.py`: `GOLD_VIEWS` (columnas esperadas), tests de
  metadatos/DDL, tests de comportamiento contra los esquemas de test y tests
  live contra `settings.database_url`. `_rows()` consulta siempre las vistas.
- `ingestor/tests/test_web_role.py`: inspecciona `relkind = 'v'` para los
  permisos de `votoscope_web`.
- Contrato de filtros: [`docs/db/gold.md`](../../docs/db/gold.md) §«Contrato
  gold ↔ front» (`election_id` + `level` + área; `election_id` +
  `polling_station_id` / `municipality_ine_code`).

## Decisiones

### 1. `gold.py`: tres funciones de DDL, una sola fuente

`view_ddl()` se queda **solo con las dos vistas de sondeos** (`poll_flat`,
`poll_trend`). Se añaden:

```python
MATVIEWS: tuple[str, ...] = (
    "election_summary",
    "result_by_area",
    "result_by_station",
    "station_turnout",
)
VIEWS: tuple[str, ...] = ("poll_flat", "poll_trend")

def matview_ddl(
    gold_schema: str = "gold", silver_schema: str = "silver"
) -> dict[str, str]: ...  # CREATE MATERIALIZED VIEW

def index_ddl(gold_schema: str = "gold") -> dict[str, str]: ...  # índices

def refresh_gold(
    session_factory: sessionmaker,
    concurrently: bool = False,
    gold_schema: str = "gold",
) -> None: ...
```

La migración y `conftest.py` consumen las tres funciones en este orden:
matviews → índices → vistas. Consecuencia deliberada: al reproducir la cadena
desde cero, `bcd8a7409aec` (que ejecuta `view_ddl()`) crea solo las dos vistas
de sondeos y la migración nueva crea las cuatro materializadas; el estado tras
`upgrade head` es el correcto. No se edita `bcd8a7409aec`.

### 2. `result_by_area`: blancos en el mismo CTE de hechos

Un único CTE `area_facts` une los votos (cuatro niveles) y los blancos
(cuatro niveles, con `party_id` nulo y `votes = 0`). El denominador se calcula
con una ventana por área, así que no hay ningún join sobre claves nulables:

```sql
CREATE MATERIALIZED VIEW {gold}.result_by_area AS
WITH area_facts AS (
    SELECT pe.election_id, 'national'::text AS level,
           NULL::text AS community_ine_code, NULL::text AS community_name,
           NULL::text AS province_ine_code, NULL::text AS province_name,
           NULL::integer AS municipality_id, NULL::text AS municipality_ine_code,
           NULL::text AS municipality_name,
           pe.party_id, v.votes::bigint AS votes, 0::bigint AS blank_votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    UNION ALL
    SELECT pe.election_id, 'community',
           p.autonomous_community_ine_code, c.name, NULL::text, NULL::text,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, v.votes::bigint, 0::bigint
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    UNION ALL
    SELECT pe.election_id, 'province',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, v.votes::bigint, 0::bigint
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    UNION ALL
    SELECT pe.election_id, 'municipality',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           m.id, m.ine_code, m.name,
           pe.party_id, v.votes::bigint, 0::bigint
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    UNION ALL
    SELECT t.election_id, 'national'::text,
           NULL::text, NULL::text, NULL::text, NULL::text,
           NULL::integer, NULL::text, NULL::text,
           NULL::integer AS party_id, 0::bigint AS votes, t.blank_votes::bigint
    FROM {silver}.turnout t
    UNION ALL
    SELECT t.election_id, 'community',
           p.autonomous_community_ine_code, c.name, NULL::text, NULL::text,
           NULL::integer, NULL::text, NULL::text,
           NULL::integer, 0::bigint, t.blank_votes::bigint
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    UNION ALL
    SELECT t.election_id, 'province',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           NULL::integer, NULL::text, NULL::text,
           NULL::integer, 0::bigint, t.blank_votes::bigint
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    UNION ALL
    SELECT t.election_id, 'municipality',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           m.id, m.ine_code, m.name,
           NULL::integer, 0::bigint, t.blank_votes::bigint
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
),
area_totals AS (
    SELECT af.election_id, af.level,
           af.community_ine_code, af.community_name,
           af.province_ine_code, af.province_name,
           af.municipality_id, af.municipality_ine_code, af.municipality_name,
           af.party_id, af.votes,
           sum(af.votes + af.blank_votes) OVER (
               PARTITION BY af.election_id, af.level, af.community_ine_code,
                            af.province_ine_code, af.municipality_id
           ) AS valid_votes
    FROM area_facts af
)
SELECT at.election_id, at.level,
       at.community_ine_code, at.community_name,
       at.province_ine_code, at.province_name,
       at.municipality_id, at.municipality_ine_code, at.municipality_name,
       p.id AS party_id, p.slug AS party_slug, p.name AS party_name,
       p.color AS party_color,
       at.votes,
       round(at.votes * 100.0 / nullif(at.valid_votes, 0), 2) AS pct
FROM area_totals at
JOIN {silver}.party p ON p.id = at.party_id
```

Notas:

- Los `::bigint` conservan el tipo de `votes` del contrato (hoy `sum(v.votes)`
  devuelve `bigint`); `valid_votes` es la suma de candidaturas y blancos del
  área, sin join.
- Los blancos entran en la ventana pero se descartan en la salida porque
  `party_id` es nulo y el join con `party` no los encuentra.
- El `INNER JOIN` anterior con `area_blank` descartaba áreas con votos y sin
  fila de participación. En datos válidos no ocurre (cada mesa con votos tiene
  su fila de `turnout`), así que el resultado sobre local es idéntico; la
  versión nueva es equivalente y no depende de esa casualidad.

`election_summary`, `result_by_station` y `station_turnout` conservan su SQL
actual; solo cambia `CREATE VIEW` por `CREATE MATERIALIZED VIEW`.

### 3. Índices

Siete índices, alineados con el contrato de `docs/db/gold.md` y con el
requisito de índice único para `REFRESH ... CONCURRENTLY` (Postgres 18 admite
`NULLS NOT DISTINCT`):

```sql
CREATE UNIQUE INDEX uq_gold_election_summary_election_id
    ON {gold}.election_summary (election_id);

CREATE UNIQUE INDEX uq_gold_result_by_area_grain
    ON {gold}.result_by_area (election_id, level, community_ine_code,
                              province_ine_code, municipality_id, party_id)
    NULLS NOT DISTINCT;
CREATE INDEX ix_gold_result_by_area_province
    ON {gold}.result_by_area (election_id, level, province_ine_code);

CREATE UNIQUE INDEX uq_gold_result_by_station_grain
    ON {gold}.result_by_station (election_id, polling_station_id, party_id);
CREATE INDEX ix_gold_result_by_station_municipality
    ON {gold}.result_by_station (election_id, municipality_ine_code);

CREATE UNIQUE INDEX uq_gold_station_turnout_grain
    ON {gold}.station_turnout (election_id, polling_station_id);
CREATE INDEX ix_gold_station_turnout_municipality
    ON {gold}.station_turnout (election_id, municipality_ine_code);
```

- El índice único de `result_by_area` cubre `election_id + level` y
  `election_id + level + community_ine_code`; el de provincia cubre el filtro
  de provincia (y el de municipio, que el contrato filtra por provincia).
- `result_by_station` y `station_turnout` cubren elección + mesa con el único
  y elección + municipio con el índice secundario.
- `election_summary` solo necesita el único por elección: la portada ordena por
  fecha sobre una relación de decenas de filas.

### 4. Refresco

```python
def refresh_gold(session_factory, concurrently=False, gold_schema="gold"):
    with session_factory() as session:
        options = {"isolation_level": "AUTOCOMMIT"} if concurrently else {}
        connection = session.connection(execution_options=options)
        for name in MATVIEWS:
            clause = "CONCURRENTLY " if concurrently else ""
            connection.execute(
                text(f"REFRESH MATERIALIZED VIEW {clause}{gold_schema}.{name}")
            )
            connection.execute(text(f"ANALYZE {gold_schema}.{name}"))
        if not concurrently:
            session.commit()
```

- **Normal**: las cuatro en una transacción (los lectores ven el cambio de
  golpe) y `ANALYZE` para que el planificador tenga estadísticas frescas.
- **Concurrente**: `REFRESH ... CONCURRENTLY` no puede ir dentro de un bloque
  de transacción; se usa una conexión `AUTOCOMMIT` y se refresca una a una.
  Exige los índices únicos de §3 (y vistas ya pobladas, que lo están desde la
  migración).
- No se añaden excepciones: los errores de SQLAlchemy suben como hoy en los
  loaders. El CLI solo captura `IngestError`.

### 5. `models.py` y `alembic check`

- Las cuatro `Table` pasan a `info={"matview": True}`; `poll_flat` y
  `poll_trend` mantienen `info={"view": True}`. No se declaran índices en
  `models.py`: el DDL de índices vive solo en `gold.py` y no interviene en el
  autogenerate (las tablas están excluidas).
- `alembic/env.py` amplía `include_object`:

  ```python
  info = getattr(object, "info", {})
  return not (type_ == "table" and (info.get("view") or info.get("matview")))
  ```

  Así el autogenerate no emite `create_table` para las matviews. El inspector
  de SQLAlchemy lista las matviews en `get_materialized_view_names()`, no en
  `get_table_names()` (`relkind` `m` ≠ `r`/`p`), de modo que `alembic check` no
  las ve como tablas que falten.
- El comentario de la sección `gold` de `models.py` se actualiza (vistas vs
  vistas materializadas).

### 6. Migración

- Revisión nueva con `down_revision = "0fa48964369e"`, creada con
  `uv run alembic revision -m "gold materialized views"` (sin
  `--autogenerate`: Alembic no genera matviews ni índices). Fichero
  `<rev>_gold_materialized_views.py`; el sufijo es el que usan los tests para
  localizarla.
- `upgrade()`:
  1. `DROP VIEW IF EXISTS gold.<name>` para las cuatro (en una base ya
     migrada existen como vistas; en una reproducción desde cero no existen
     porque `view_ddl()` ya solo devuelve las de sondeos).
  2. `matview_ddl()` (creación `WITH DATA`, poblada).
  3. `index_ddl()`.
  4. `ANALYZE` y `GRANT SELECT ... TO votoscope_web` por matview.
- `downgrade()`: `DROP MATERIALIZED VIEW IF EXISTS` de las cuatro, recreación
  de las cuatro vistas con el SQL anterior **congelado en el propio fichero de
  migración** (no se edita `bcd8a7409aec` ni se duplica el SQL en `gold.py`),
  y `GRANT SELECT` de las vistas recreadas.
- El SQL de la migración no se escribe inline salvo el `downgrade` histórico:
  `upgrade` ejecuta las funciones de `gold.py`, igual que `bcd8a7409aec`.

### 7. CLI

En `ingestor/src/ingestor/cli.py`:

```python
refresh = subparsers.add_parser(
    "refresh-gold",
    help="refresh the gold materialized views (--concurrently avoids read locks)",
)
refresh.add_argument("--concurrently", action="store_true")

# ...
if args.command == "refresh-gold":
    refresh_gold(SessionLocal, concurrently=args.concurrently)
    return 0
```

Al final de `ingest`, tras `ingest_path` y dentro del `try` existente:

```python
if any(outcome.status == "processed" for outcome in outcomes):
    refresh_gold(SessionLocal)
```

- Una sola llamada por ejecución, fuera del bucle de `ingest_path`.
- `load-geography` no refresca (no cambia hechos).
- `ingest-polls` no toca el refresco.
- `refresh-gold` es idempotente por naturaleza; ejecutarlo dos veces no cambia
  el contenido.

### 8. Permisos de `votoscope_web`

`GRANT SELECT ON ALL TABLES IN SCHEMA gold` y los privilegios por defecto de
`9f3c2a1b7d40` ya cubren las matviews creadas después, pero la migración nueva
concede `SELECT` explícito por matview (defensa ante ejecuciones con otro rol
propietario). No se conceden `INSERT`/`UPDATE`/`DELETE`/`TRUNCATE` ni `CREATE`.
Los tests de `test_web_role.py` pasan de `relkind = 'v'` a `relkind IN ('v','m')`
para que las matviews entren en la comprobación.

### 9. ERD y documentación

- `docs/db/schema.drawio`, página Gold: título «Votoscope — gold (vistas
  materializadas y vistas)» y una celda de nota `g_matviews_note` con las
  cuatro matviews, sus índices y `refresh-gold`; las cajas de las matviews
  mantienen `value = <nombre>` (el test compara el nombre exacto) y no llevan
  marcadores PK/FK.
- `.agents/data-model.md` §`gold`: cuatro matviews + dos vistas, índices y
  refresco.
- `.agents/architecture.md`: «seis vistas» → cuatro vistas materializadas y dos
  vistas; flujo `gold (matviews y vistas)`; refresco al final de `ingest`.
- `docs/db/gold.md`: tabla de relaciones con columna «tipo»
  (materializada/vista), sección «Refresco» (`ingest`, `refresh-gold`,
  `ingest-polls` no refresca, datos pueden quedar obsoletos hasta el refresco).
- `docs/ingestor/ingesta.md`: comando `refresh-gold [--concurrently]` y
  refresco al final de `ingest`.
- `ingestor/AGENTS.md`: `gold.py` (tres DDL + `refresh_gold`), comandos y
  migración.
- `.agents/status.md`: relación de migraciones y estado de `gold`.

### 10. Tests

| Test | Tipo | Cubre |
| --- | --- | --- |
| `test_models_declare_gold_views` (actualizado) | hermético | R16 |
| `test_gold_ddl_functions` (sustituye a `test_view_ddl_is_single_source`) | hermético | R3, R4, R5, R6 |
| `test_result_by_area_sql_has_no_nullable_join` (nuevo) | hermético | R1 |
| `test_poll_trend_keeps_order_by` (nuevo) | hermético | R7 |
| `test_migration_executes_matview_ddl` (nuevo) | hermético | R3, R4, R5, R25 |
| `test_env_skips_views_and_matviews` (nuevo) | hermético | R17 |
| `test_alembic_check_has_no_drift` (nuevo) | live | R17 |
| `test_test_schema_has_gold_matviews` (nuevo) | esquemas de test | R21, R22 |
| `test_refresh_gold_updates_matviews` (nuevo) | esquemas de test | R23 |
| `test_refresh_gold_is_idempotent` (nuevo) | esquemas de test | R12, R23 |
| `test_refresh_gold_concurrently` (nuevo) | esquemas de test | R13, R14, R24 |
| `test_cli_refresh_gold` (nuevo) | hermético (monkeypatch) | R10, R11, R13, R14 |
| `test_ingest_refreshes_gold_once` (nuevo) | integración CLI | R8 |
| `test_ingest_skipped_does_not_refresh` (nuevo) | integración CLI | R9 |
| `test_ingest_polls_does_not_refresh` (nuevo) | integración CLI | R15 |
| `test_result_by_area_matches_legacy_sql_on_local` (nuevo) | live | R2 |
| `test_result_by_area_regression_seeded` (nuevo) | esquemas de test | R2 |
| `test_live_gold_relations_match_models` (actualiza `test_live_gold_views_match_models`) | live | R3, R6, R21, R22 |
| `test_live_gold_matview_indexes` (nuevo) | live | R4, R5 |
| `test_web_role_*` (actualizados) | live | R25, R26 |
| `test_results_contract_under_50ms` (nuevo) | live | R27 |
| `test_docs_*` y `test_drawio_gold_page` (ampliados) | hermético | R18, R19, R20 |

Detalles de los tests que no son obvios:

- **`_rows()` refresca**: las matviews son snapshots; en el esquema de test,
  `_rows()` ejecuta `refresh_gold(db, gold_schema="polls_test_gold")` antes de
  consultar una matview. Las vistas de sondeos se consultan sin refresco.
- **Regresión local**: el test live ejecuta como oráculo el SQL anterior de
  `result_by_area` (copiado en el test, con `area_blank` y
  `IS NOT DISTINCT FROM`) contra `silver` y compara fila a fila con
  `gold.result_by_area`. Se salta si no hay elecciones cargadas.
- **<50 ms**: `EXPLAIN (ANALYZE, FORMAT JSON)` sobre las consultas del contrato
  de resultados (portada, nacional, CCAA, provincia, municipio, mesa y mesas
  del municipio), con una pasada de calentamiento y la mejor de tres; se salta
  sin base o sin datos. La medición manual se anota en
  `progress/impl_gold_matviews.md`.
- **CLI**: los tests de `ingest` reutilizan el patrón `_use_cli` de
  `test_polls_load.py` (monkeypatch de `SessionLocal`, `configure_logging` y
  `settings.raw_dir`) y cuentan las llamadas a `refresh_gold`.

## Alternativas descartadas

1. **Mantener las seis en `view_ddl()` con cuatro convertidas en matviews**:
   la migración vieja `bcd8a7409aec` crearía matviews en una reproducción desde
   cero (sin índices), el nombre de la función mentiría y el refresco
   dependería de una migración posterior. Se prefiere separar
   `view_ddl`/`matview_ddl`/`index_ddl`; el estado final es el mismo y cada
   función dice lo que hace.
2. **Duplicar en `gold.py` el SQL viejo de `result_by_area` para conservar la
   reproducción histórica**: dos definiciones de la misma vista invitan a
   divergir. El SQL viejo queda congelado solo en el `downgrade` de la
   migración nueva.
3. **Refresco por trigger o `pg_cron`**: exige extensiones/permisos y no es lo
   que pide el acceptance (refresco al final de `ingest` + comando manual).
4. **Refrescar en cada consulta o desde la web**: la web es de solo lectura y
   no puede refrescar; además multiplicaría el coste.
5. **Declarar los índices en `models.py`**: duplicaría el DDL de `gold.py` sin
   que el autogenerate los gestione (las tablas están excluidas). Los tests
   live comprueban los índices reales.
6. **`REFRESH ... CONCURRENTLY` dentro de una transacción**: Postgres lo
   prohíbe; de ahí la conexión `AUTOCOMMIT` del modo concurrente.

## Regla de oro del modelo de datos

Esta feature no añade tablas ni columnas, pero cambia la naturaleza de cuatro
relaciones de `gold`; los tres sitios quedan:

1. **ERD** — `docs/db/schema.drawio`, página Gold: nota de matviews e índices.
2. **Modelos** — `ingestor/src/ingestor/models.py`: `info={"matview": True}` en
   las cuatro, `info={"view": True}` en las dos de sondeos; columnas y tipos
   intactos.
3. **Migración** — `ingestor/alembic/versions/<rev>_gold_materialized_views.py`:
   drop de las vistas, creación de las matviews, índices, `ANALYZE`, permisos y
   `downgrade` con el SQL histórico congelado.

## Riesgos y notas

- La creación de las matviews en la migración recorre todos los hechos (en
  local, `result_by_area` tardaba ~12 s como vista); `alembic upgrade head`
  tardará más de lo habitual una vez. Es coste de una sola ejecución.
- `REFRESH ... CONCURRENTLY` bloquea menos pero es más lento y exige los
  índices únicos; el modo normal es el que usa `ingest`.
- Si en el futuro se añade una quinta relación de resultados, debe entrar en
  `MATVIEWS`, en `index_ddl()`, en el ERD y en la documentación; el test
  `test_gold_ddl_functions` fija el conjunto actual.
