# Diseño — `delivery_gold`

Feature 15 de [`feature_list.json`](../../feature_list.json). Entrega el esquema `gold` —seis vistas de solo lectura: resultados electorales y sondeos—, el contrato que consumirá `web/` ([`docs/db/gold.md`](../../docs/db/gold.md)) y la topología de entornos. No toca `web/`: la feature 16 lee estas vistas sin redefinir nada.

Depende de las features 12–14 (van antes en la cola): el catálogo `party_catalog.toml` y el resolver `parties.py` resuelven la identidad de `party`, con `party.color` aún nulo — esta feature **cierra la curación de color** que [`data-model.md`](../../.agents/data-model.md) sitúa «al construir `gold`» (R18–R22). Sin cambios en `silver` salvo `party.color`; sin dependencias nuevas (`sqlalchemy`/`alembic` ya están); sin CLI nueva; sin excepciones nuevas (`IngestError`).

## Estado observado al redactar (2026-10-18, local; no congelado)

- `silver`: 13 elecciones `congress` nacionales cargadas (2023-07-23 = `election.id 1`), 6.047.666 votos, 106.243 mesas; `pollster`/`poll`/`poll_result` con 28/575/6.125 filas (revisión `1380859635`); 549 `party`, **0 con color**; el esquema `gold` existe vacío en la base local (sin objetos).
- El SQL de las seis vistas está **validado contra ese `silver`** (SELECTs de prototipo, sin crear nada): los totales cuadran (2023 nacional: PP 8.161.117 votes / 33,06 %; PSOE 7.821.777 / 31,68 %; censo 37.469.141; participación 66,60 %), el grano de `result_by_area` es único por (elección, nivel, área, partido) y el filtro del front empuja a los índices (ver §Decisiones).

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/gold.py` — `view_ddl()`, única fuente de las sentencias de las vistas |
| modificar | `ingestor/src/ingestor/models.py` — seis `Table` de `gold` (sección nueva) |
| modificar | `ingestor/alembic/env.py` — `include_object` que excluye las vistas del autogenerate |
| crear | `ingestor/alembic/versions/<rev>_gold_views.py` — migración (esquema + vistas) |
| modificar | `ingestor/tests/conftest.py` — esquema `gold` de test y creación de las vistas en él |
| crear | `ingestor/tests/test_gold.py` — R1, R2, R5–R22 |
| modificar | `ingestor/tests/test_polls_model.py` — tupla de páginas del ERD con «Gold» |
| modificar | `docs/db/schema.drawio` — página «Gold» |
| crear | `docs/db/gold.md` — contrato gold ↔ front |
| modificar | `.agents/environment.md` · `.agents/data-model.md` · `.agents/architecture.md` · `docs/ingestor/ingesta.md` · `ingestor/AGENTS.md` · `web/AGENTS.md` (puntero al contrato) |
| modificar | `ingestor/src/ingestor/data/party_catalog.toml` · `ingestor/src/ingestor/parties.py` — color curado |
| crear | `progress/impl_delivery_gold.md` — evidencia de la recarga y trazabilidad R ↔ test |

## La regla de oro, al detalle

### 1. ERD — `docs/db/schema.drawio` (página «Gold», nueva)

- Una página nueva **«Gold»** con título `Votoscope — gold (vistas para la web)` y un contenedor por vista (`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat`, `poll_trend`), con las columnas de §Las seis vistas (fila `value="<columna> <tipo>"`, patrón de las páginas existentes para que el test las lea por `value.split()[0]`).
- Las vistas no tienen PK ni FK: la columna de constraints queda vacía (o con `-`); **no hay aristas crow's foot** entre vistas (el validador de la skill `database-erd-drawio` solo admite `entityRelationEdgeStyle` entre anclas de fila de tabla, y aquí no hay relaciones). Si se dibujan cajas de referencia de `silver` (opcional), van atenuadas (`opacity`/`#f5f5f5`) como `party`/`election` en «Silver polls».
- Las páginas «Bronze», «Silver», «Bronze polls» y «Silver polls» no se tocan. La regla de `data-model.md` pasa a «(Bronze, Silver, Bronze polls, Silver polls, Gold)» — R16 — y con ella **dos aserciones de `test_polls_model.py`** (`test_drawio_has_a_page_per_schema_and_domain` y `test_data_model_documents_page_per_schema_and_domain`): se actualiza la tupla literal.

### 2. Modelos — `ingestor/src/ingestor/models.py`

Sección nueva al final (tras silver), con un `Table` de SQLAlchemy Core por vista — son vistas de solo lectura: sin PK, sin FK, sin índices, `schema="gold"` e `info={"view": True}`:

```python
# ------------------------------------------------------------------- gold

# Read-only views for the web frontend. They are not tables: no PK/FK; the
# migration creates them from gold.view_ddl() and alembic/env.py skips them
# in autogenerate (info["view"]).

election_summary = Table(
    "election_summary",
    Base.metadata,
    Column("election_id", Integer, nullable=False),
    Column("election_type", String(20), nullable=False),
    Column("election_date", Date, nullable=False),
    Column("election_name", Text, nullable=True),
    Column("census", BigInteger, nullable=False),
    Column("null_votes", BigInteger, nullable=False),
    Column("blank_votes", BigInteger, nullable=False),
    Column("candidature_votes", BigInteger, nullable=False),
    Column("valid_votes", BigInteger, nullable=False),
    Column("voters", BigInteger, nullable=False),
    Column("turnout_pct", Numeric, nullable=True),
    schema="gold",
    info={"view": True},
)

result_by_area = Table(...)
# … el resto (columnas y tipos en §Las seis vistas)
```

- Imports nuevos en `models.py`: `Column`, `Integer`, `Table` (los demás ya están: `BigInteger`, `Date`, `Numeric`, `String`, `Text`).
- Tipos declarados = los que la vista produce: los `sum()` de enteros son `BigInteger`; los `round(numeric, 2)` son `Numeric`; las columnas que pasan por `UNION ALL` con `NULL::text` son `Text` (el tipo resuelto por Postgres); las columnas que no pasan por unión conservan el tipo del origen (`String(60)` en `party_slug`, `String(5)` en `municipality_ine_code` de `result_by_station`…). El test live compara **nombres** y unos tipos representativos, no `typmod`s (en las vistas con `UNION` el tipo resuelto lo decide la base).

### 3. Migración — `ingestor/alembic/versions/<rev>_gold_views.py`

- `uv run alembic revision -m "gold views"` (sin `--autogenerate`: autogenerate no genera vistas y `include_object` las filtra; la revisión nace vacía con el `down_revision` correcto).
- `upgrade()`: `op.execute("CREATE SCHEMA IF NOT EXISTS gold")` y, en orden, `op.execute(ddl)` de cada sentencia de `gold.view_ddl()`. `downgrade()`: `DROP VIEW IF EXISTS gold.<nombre>` en orden inverso. **El DDL vive solo en la migración** (nunca a mano); las vistas no se editan: un cambio de columnas/SQL es otra migración con `view_ddl()` actualizado.
- `env.py` gana el filtro para que `alembic check` no pida `create_table` de las vistas (metadata ≠ tablas):

```python
def include_object(
    object: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Skip gold views: they are created by the migration, not by create_table."""
    if type_ == "table" and getattr(object, "info", {}).get("view"):
        return False
    return True
```

  conectado en `run_migrations_online` y `run_migrations_offline` (`context.configure(..., include_object=include_object)`). Limitación documentada: `alembic check` no detecta drift *dentro* de una vista (el SQL); lo cubren los tests (la metadata ↔ la vista reflejada en el esquema de test y en la base real) y el contrato de §Las seis vistas.

### `gold.py` — única fuente del SQL (R2)

```python
"""Gold layer: read-only views for the web frontend.

Single source for the view SQL: the alembic migration executes these statements
and the tests create the same views in throwaway schemas.
"""

_VIEW_SQL: dict[str, str] = {
    "election_summary": """CREATE VIEW {gold}.election_summary AS
SELECT ...""",
    # result_by_area, result_by_station, station_turnout, poll_flat, poll_trend
}


def view_ddl(gold_schema: str = "gold", silver_schema: str = "silver") -> dict[str, str]:
    """Return the ``CREATE VIEW`` statements by view name, schema-parametrised."""
    return {
        name: sql.format(gold=gold_schema, silver=silver_schema)
        for name, sql in _VIEW_SQL.items()
    }
```

El SQL no contiene `%` ni llaves salvo los marcadores. El orden de las claves es el de creación (resultados primero, sondeos después); no hay dependencias entre vistas.

## Las seis vistas (contrato de columnas)

### `election_summary` — una fila por elección con hechos

| Columna | Tipo (modelo) | Descripción |
| --- | --- | --- |
| `election_id` | Integer | `silver.election.id` |
| `election_type` | String(20) | `congress`… |
| `election_date` | Date | fecha de la elección |
| `election_name` | Text (NULL) | nombre (hoy nulo en `silver`) |
| `census` | BigInteger | Σ censo de las mesas |
| `null_votes` | BigInteger | Σ nulos |
| `blank_votes` | BigInteger | Σ blancos |
| `candidature_votes` | BigInteger | Σ votos a candidaturas |
| `valid_votes` | BigInteger | candidaturas + blancos |
| `voters` | BigInteger | válidos + nulos |
| `turnout_pct` | Numeric | votantes / censo × 100, 2 decimales (NULL si censo 0) |

SQL:

```sql
CREATE VIEW {gold}.election_summary AS
SELECT e.id AS election_id,
       e.type AS election_type,
       e.date AS election_date,
       e.name AS election_name,
       t.census, t.null_votes, t.blank_votes,
       coalesce(vt.candidature_votes, 0) AS candidature_votes,
       coalesce(vt.candidature_votes, 0) + t.blank_votes AS valid_votes,
       coalesce(vt.candidature_votes, 0) + t.blank_votes + t.null_votes AS voters,
       round((coalesce(vt.candidature_votes, 0) + t.blank_votes + t.null_votes) * 100.0
             / nullif(t.census, 0), 2) AS turnout_pct
FROM {silver}.election e
JOIN (
    SELECT election_id, sum(census) AS census, sum(null_votes) AS null_votes,
           sum(blank_votes) AS blank_votes
    FROM {silver}.turnout GROUP BY election_id
) t ON t.election_id = e.id
LEFT JOIN (
    SELECT pe.election_id, sum(v.votes) AS candidature_votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY pe.election_id
) vt ON vt.election_id = e.id;
```

### `result_by_area` — una fila por (elección, nivel, área, partido)

| Columna | Tipo (modelo) | Descripción |
| --- | --- | --- |
| `election_id` | Integer | elección |
| `level` | Text | `national` \| `community` \| `province` \| `municipality` |
| `community_ine_code` / `community_name` | Text (NULL) | CCAA (nivel `community` o inferior) |
| `province_ine_code` / `province_name` | Text (NULL) | provincia (nivel `province` o inferior) |
| `municipality_id` / `municipality_ine_code` / `municipality_name` | Integer / Text / Text (NULL) | municipio (nivel `municipality`) |
| `party_id` / `party_slug` / `party_name` / `party_color` | Integer / String(60) / Text / String(7) (NULL) | identidad del partido |
| `votes` | BigInteger | votos del partido en el área (suma de sus candidaturas) |
| `pct` | Numeric | votos / válidos del área × 100 (2 decimales; NULL si denominador 0) |

SQL (joins repetidos por rama **a propósito**: ver §Decisiones):

```sql
CREATE VIEW {gold}.result_by_area AS
WITH area_votes AS (
    SELECT pe.election_id, 'national'::text AS level,
           NULL::text AS community_ine_code, NULL::text AS community_name,
           NULL::text AS province_ine_code, NULL::text AS province_name,
           NULL::integer AS municipality_id, NULL::text AS municipality_ine_code,
           NULL::text AS municipality_name,
           pe.party_id, sum(v.votes) AS votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    UNION ALL
    SELECT pe.election_id, 'community',
           p.autonomous_community_ine_code, c.name, NULL::text, NULL::text,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 10
    UNION ALL
    SELECT pe.election_id, 'province',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           NULL::integer, NULL::text, NULL::text,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 5, 6, 10
    UNION ALL
    SELECT pe.election_id, 'municipality',
           p.autonomous_community_ine_code, c.name, p.ine_code, p.name,
           m.id, m.ine_code, m.name,
           pe.party_id, sum(v.votes)
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    JOIN {silver}.polling_station s ON s.id = v.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
    GROUP BY 1, 3, 4, 5, 6, 7, 8, 9, 10
),
area_blank AS (
    SELECT t.election_id, 'national'::text AS level,
           NULL::text AS community_ine_code, NULL::text AS province_ine_code,
           NULL::integer AS municipality_id,
           sum(t.blank_votes) AS blank_votes
    FROM {silver}.turnout t
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'community', p.autonomous_community_ine_code, NULL::text,
           NULL::integer, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'province', p.autonomous_community_ine_code, p.ine_code,
           NULL::integer, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
    UNION ALL
    SELECT t.election_id, 'municipality', p.autonomous_community_ine_code, p.ine_code,
           m.id, sum(t.blank_votes)
    FROM {silver}.turnout t
    JOIN {silver}.polling_station s ON s.id = t.polling_station_id
    JOIN {silver}.municipality m ON m.id = s.municipality_id
    JOIN {silver}.province p ON p.ine_code = m.province_ine_code
    GROUP BY 1, 2, 3, 4, 5
),
area_totals AS (
    SELECT av.*,
           sum(av.votes) OVER (
               PARTITION BY av.election_id, av.level, av.community_ine_code,
                            av.province_ine_code, av.municipality_id
           ) AS candidature_votes
    FROM area_votes av
)
SELECT at.election_id, at.level,
       at.community_ine_code, at.community_name,
       at.province_ine_code, at.province_name,
       at.municipality_id, at.municipality_ine_code, at.municipality_name,
       p.id AS party_id, p.slug AS party_slug, p.name AS party_name,
       p.color AS party_color,
       at.votes,
       round(at.votes * 100.0 / nullif(at.candidature_votes + ab.blank_votes, 0), 2) AS pct
FROM area_totals at
JOIN area_blank ab
  ON ab.election_id = at.election_id
 AND ab.level = at.level
 AND ab.community_ine_code IS NOT DISTINCT FROM at.community_ine_code
 AND ab.province_ine_code IS NOT DISTINCT FROM at.province_ine_code
 AND ab.municipality_id IS NOT DISTINCT FROM at.municipality_id
JOIN {silver}.party p ON p.id = at.party_id;
```

### `result_by_station` — una fila por (elección, mesa, partido)

Columnas: `election_id` Integer · `polling_station_id` Integer · `district` String(2) · `section` String(4) · `code` String(1) · `municipality_id` Integer · `municipality_ine_code` String(5) · `municipality_name` Text (NULL) · `province_ine_code` String(2) · `province_name` Text · `community_ine_code` String(2) · `community_name` Text · `party_id` Integer · `party_slug` String(60) · `party_name` Text · `party_color` String(7) (NULL) · `votes` BigInteger · `pct` Numeric — mismo cálculo que R11 a nivel de mesa.

```sql
CREATE VIEW {gold}.result_by_station AS
WITH station_party AS (
    SELECT v.polling_station_id, pe.election_id, pe.party_id, sum(v.votes) AS votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2, 3
),
station_valid AS (
    SELECT polling_station_id, election_id, sum(votes) AS candidature_votes
    FROM station_party
    GROUP BY 1, 2
)
SELECT sp.election_id, sp.polling_station_id,
       s.district, s.section, s.code,
       m.id AS municipality_id, m.ine_code AS municipality_ine_code, m.name AS municipality_name,
       p.ine_code AS province_ine_code, p.name AS province_name,
       c.ine_code AS community_ine_code, c.name AS community_name,
       pa.id AS party_id, pa.slug AS party_slug, pa.name AS party_name,
       pa.color AS party_color,
       sp.votes,
       round(sp.votes * 100.0 / nullif(sv.candidature_votes + t.blank_votes, 0), 2) AS pct
FROM station_party sp
JOIN station_valid sv ON sv.polling_station_id = sp.polling_station_id
                     AND sv.election_id = sp.election_id
JOIN {silver}.polling_station s ON s.id = sp.polling_station_id
JOIN {silver}.municipality m ON m.id = s.municipality_id
JOIN {silver}.province p ON p.ine_code = m.province_ine_code
JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
JOIN {silver}.turnout t ON t.polling_station_id = sp.polling_station_id
                       AND t.election_id = sp.election_id
JOIN {silver}.party pa ON pa.id = sp.party_id;
```

### `station_turnout` — una fila por (elección, mesa)

Columnas: las de identidad/geografía de `result_by_station` sin partido, más `census` Integer · `null_votes` Integer · `blank_votes` Integer · `candidature_votes` BigInteger · `valid_votes` BigInteger · `voters` BigInteger · `turnout_pct` Numeric.

```sql
CREATE VIEW {gold}.station_turnout AS
WITH station_valid AS (
    SELECT v.polling_station_id, pe.election_id, sum(v.votes) AS candidature_votes
    FROM {silver}.vote v
    JOIN {silver}.party_election pe ON pe.id = v.party_election_id
    GROUP BY 1, 2
)
SELECT t.election_id, t.polling_station_id,
       s.district, s.section, s.code,
       m.id AS municipality_id, m.ine_code AS municipality_ine_code, m.name AS municipality_name,
       p.ine_code AS province_ine_code, p.name AS province_name,
       c.ine_code AS community_ine_code, c.name AS community_name,
       t.census, t.null_votes, t.blank_votes,
       coalesce(sv.candidature_votes, 0) AS candidature_votes,
       coalesce(sv.candidature_votes, 0) + t.blank_votes AS valid_votes,
       coalesce(sv.candidature_votes, 0) + t.blank_votes + t.null_votes AS voters,
       round((coalesce(sv.candidature_votes, 0) + t.blank_votes + t.null_votes) * 100.0
             / nullif(t.census, 0), 2) AS turnout_pct
FROM {silver}.turnout t
JOIN {silver}.polling_station s ON s.id = t.polling_station_id
JOIN {silver}.municipality m ON m.id = s.municipality_id
JOIN {silver}.province p ON p.ine_code = m.province_ine_code
JOIN {silver}.autonomous_community c ON c.ine_code = p.autonomous_community_ine_code
LEFT JOIN station_valid sv ON sv.polling_station_id = t.polling_station_id
                          AND sv.election_id = t.election_id;
```

### `poll_flat` — una fila por (sondeo, partido)

Columnas: `poll_id` Integer · `pollster_id` Integer · `pollster_slug` String(60) · `pollster_name` Text · `source` Text · `election_type` String(20) · `election_id` Integer (NULL) · `fieldwork_start` Date (NULL) · `fieldwork_end` Date (NULL) · `sample_size` Integer (NULL) · `turnout` Numeric(5,2) (NULL) · `revision_id` BigInteger · `party_id` Integer · `party_slug` String(60) · `party_name` Text · `party_color` String(7) (NULL) · `pct` Numeric(5,2) (NULL) · `seats_min` Integer (NULL) · `seats_max` Integer (NULL).

```sql
CREATE VIEW {gold}.poll_flat AS
SELECT p.id AS poll_id,
       ps.id AS pollster_id, ps.slug AS pollster_slug, ps.name AS pollster_name,
       p.source, p.election_type, p.election_id,
       p.fieldwork_start, p.fieldwork_end, p.sample_size, p.turnout, p.revision_id,
       pt.id AS party_id, pt.slug AS party_slug, pt.name AS party_name,
       pt.color AS party_color,
       r.pct, r.seats_min, r.seats_max
FROM {silver}.poll_result r
JOIN {silver}.poll p ON p.id = r.poll_id
JOIN {silver}.pollster ps ON ps.id = p.pollster_id
JOIN {silver}.party pt ON pt.id = r.party_id;
```

### `poll_trend` — una fila por (sondeo, partido), ordenada por trabajo de campo

Columnas: `poll_id` Integer · `poll_date` Date (NULL) · `pollster_slug` String(60) · `pollster_name` Text · `source` Text · `revision_id` BigInteger · `election_type` String(20) · `election_id` Integer (NULL) · `party_id` Integer · `party_slug` String(60) · `party_name` Text · `party_color` String(7) (NULL) · `pct` Numeric(5,2) (NULL) · `seats_min` Integer (NULL) · `seats_max` Integer (NULL).

```sql
CREATE VIEW {gold}.poll_trend AS
SELECT p.id AS poll_id,
       coalesce(p.fieldwork_end, p.fieldwork_start) AS poll_date,
       ps.slug AS pollster_slug, ps.name AS pollster_name,
       p.source, p.revision_id, p.election_type, p.election_id,
       pt.id AS party_id, pt.slug AS party_slug, pt.name AS party_name,
       pt.color AS party_color,
       r.pct, r.seats_min, r.seats_max
FROM {silver}.poll_result r
JOIN {silver}.poll p ON p.id = r.poll_id
JOIN {silver}.pollster ps ON ps.id = p.pollster_id
JOIN {silver}.party pt ON pt.id = r.party_id
ORDER BY poll_date, p.id, pt.slug;
```

- `ORDER BY poll_date` en `ASC` deja los NULL al final (default de Postgres). La vista **no filtra**: los porcentajes nulos (`?`/`<2.0` de la fuente) y los partidos sin color salen tal cual y los decide el front.
- El orden de una vista se conserva al consultarla sin `ORDER BY`; el test lo fija además por `pg_get_viewdef`.

## Semántica congelada (R11)

- **Votos válidos** = votos a candidaturas + blancos. **Votantes** = válidos + nulos (la definición de `silver.turnout`, ya usada por la ingesta).
- **`pct` de resultados** = votos del partido / (Σ votos a candidaturas del área o mesa + blancos del área o mesa) × 100, redondeado a 2; NULL si el denominador es 0 (`nullif`). Los votos del partido suman sus candidaturas (`party_election` → `party`), la misma identidad curada que usan los sondeos.
- **`turnout_pct`** = votantes / censo × 100, redondeado a 2; NULL si censo 0.
- CERA y municipios extintos entran por la geografía normal (`municipality_name` puede ser NULL); no hay tratamiento especial.

## El contrato — `docs/db/gold.md` (R13)

Documento nuevo, orientado a la web (feature 16), con esta estructura y subcadenas estables para el test:

```markdown
# Esquema gold: vistas y contrato con la web

`gold` contiene solo vistas de solo lectura; la web las consulta en servidor
(Server Components) y no agrega hechos: los totales y porcentajes vienen
calculados por las vistas. Nunca se leen tablas `silver` desde la web.

## Vistas

| Vista | Grano | Consulta |

## Contrato gold ↔ front

| Pantalla | Vista(s) | Filtro / orden |
| --- | --- | --- |
| Resultados — portada (última general) | `election_summary` | `order by election_date desc limit 1` |
| Resultados — nacional | `result_by_area` | `election_id = … and level = 'national'` |
| Resultados — mapa de CCAA | `result_by_area` | `level = 'community'` |
| Resultados — provincia | `result_by_area` | `level = 'province' and community_ine_code = …` |
| Resultados — municipio | `result_by_area` | `level = 'municipality' and province_ine_code = …` |
| Resultados — mesas del municipio | `station_turnout` + `result_by_station` | `election_id = … and municipality_ine_code = …` |
| Resultados — detalle de mesa | `station_turnout` + `result_by_station` | `polling_station_id = …` |
| Sondeos — tendencia | `poll_trend` | series por `party_slug`, x = `poll_date` |
| Sondeos — tabla | `poll_flat` | agrupable por `pollster_slug`; fechas, `pct`, escaños, `source`/`revision_id` |

## Semántica

(votos válidos, `pct`, `turnout_pct`, `level`, NULLs de `party_color` y
`municipality_name`; la web no agrega hechos)

## Aplicación y verificación

(`uv run alembic upgrade head`; solo lectura; el rol de la web se crea en la
feature 16)
```

## Topología de entornos — `.agents/environment.md` (R14)

Sección nueva «Topología de entornos» (además de ajustar la sección de la web con el puntero al contrato):

```markdown
## Topología de entornos

Dos entornos, sin staging (el MVP se entrega con estos dos):

| Pieza | Local (hoy) | Producción (entrega) |
| --- | --- | --- |
| Postgres | docker-compose (host 5434), datos reales | Postgres gestionado (Neon) |
| Ingestador | `uv run ingestor …` en la máquina; cron/launchd 2×/día para los sondeos (feature 10) | job programado de GitHub Actions (`.github/workflows/polls-sync.yml`, hoy placeholder) con `DATABASE_URL` en secrets; ingestas de elecciones y recargas de curación a mano contra la base |
| Web | `next dev` contra el Postgres local | Vercel; lee `gold` en servidor con un rol de solo lectura (feature 16) |
| Migraciones | `uv run alembic upgrade head` antes de ingerir | `uv run alembic upgrade head` contra la base de producción antes de ingerir |
| Secretos | `ingestor/.env` (gitignored) | `DATABASE_URL` en Vercel (solo servidor) y en GitHub secrets; nunca en el cliente |

El workflow `polls-sync.yml` sigue en placeholder hasta que exista el entorno:
esta sección fija la decisión, el cableado llega con el despliegue.
```

## Curación de color (R18–R22)

- **Catálogo** (`party_catalog.toml`): clave opcional `color = "#rrggbb"` en cada ficha; hex en minúsculas o mayúsculas (el test no lo exige). La ficha de sondeos que solo existe en el catálogo (p. ej. `salf`) también lleva color.
- **`parties.py`**: `PartyEntry` gana `color: str | None = None`; `load_catalog` valida `^#[0-9a-fA-F]{6}$` y lanza `IngestError` con la ruta y el slug de la ficha si no casa (R19). El resolver aplica el color al resolver:

```python
entry = self.catalog.lookup(label)
if entry is not None:
    party = self.by_slug.get(entry.slug) or Party(name=entry.name, slug=entry.slug)
    if entry.color is not None:
        party.color = entry.color       # también recolorea filas existentes
    self._index(party)
    return party
```

- **Valores**: las 15 marcas de sondeos (`pp`, `psoe`, `vox`, `sumar`, `podemos`, `erc`, `jxcat-junts`, `eh-bildu`, `eaj-pnv`, `bng`, `cca`, `u-p-n`, `salf`, `adelante-andalucia`, `alianca-cat`) y las fichas de las marcas principales del 2023 que ya tenga el catálogo; se aprueban en el diff (misma mecánica que los alias de la 12). Los partidos sin ficha quedan a NULL y la web usa su color por defecto.
- **Materialización**: es el bucle de curación de la 12 — `uv run ingestor ingest --force` (los 13 procesos, como la 13) e `uv run ingestor ingest-polls --force`. Verificación:

```sql
SELECT p.slug FROM silver.party p
JOIN silver.poll_result pr ON pr.party_id = p.id
WHERE p.color IS NULL GROUP BY 1;   -- vacío para las 15 marcas
```

## Tests

### `ingestor/tests/conftest.py` (delta)

- `TEST_SCHEMAS` añade `"gold": "polls_test_gold"` (el esquema se crea y se borra con los demás).
- `BASE_TABLES = [t for t in Base.metadata.sorted_tables if not t.info.get("view")]`: `Base.metadata.create_all(engine, tables=BASE_TABLES)` y el vaciado por test (`reversed(BASE_TABLES)` → `delete()`) **ignoran las vistas** (no se crean como tablas ni se pueden vaciar).
- Tras `create_all`, con `engine.begin()`: `for ddl in view_ddl(gold_schema="polls_test_gold", silver_schema="polls_test_silver").values(): connection.exec_driver_sql(ddl)`.
- El resto de la fixture (translate map, skip sin Postgres, limpieza) no cambia; los tests de las features 9–14 siguen verdes.

### `ingestor/tests/test_gold.py`

Sin red. Metadata sin BD:

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_models_declare_gold_views` | R1 | las seis `Table` en `Base.metadata.tables["gold.<vista>"]`, `info["view"]`, sin PK/FK, columnas por vista |
| `test_view_ddl_is_single_source` | R2 | claves de `view_ddl()` = las seis vistas; `CREATE VIEW {gold}<vista>`; parametrización de esquemas |
| `test_silver_metadata_has_no_new_aggregates` | R12 | el conjunto de tablas y columnas de `bronze`/`silver` en `Base.metadata` es el esperado (sin agregados nuevos) |
| `test_catalog_parses_color` | R18 | ficha con `color` → `PartyEntry.color`; ficha sin `color` → None |
| `test_catalog_rejects_invalid_color` | R19 | `#12345`, `red`, `#12345g` → `IngestError` con la ficha |
| `test_resolver_applies_color` | R20 | fila existente recoloreada; fila creada con el color; ficha sin color deja la fila intacta |
| `test_catalog_poll_labels_have_colors` | R21 | las 15 etiquetas de sondeos resuelven a fichas con `color` válido |
| `test_docs_gold_contract` | R13 | subcadenas de `docs/db/gold.md` (vistas, «Pantalla», «Resultados», «Sondeos», `level`, `party_color`, «no agrega») |
| `test_docs_environment_topology` | R14 | subcadenas de `.agents/environment.md` («Topología de entornos», `docker-compose`, `Vercel`, `Neon`, `GitHub Actions`, «solo lectura») |
| `test_docs_data_model_gold` | R16 | tupla de páginas con «Gold», las seis vistas en el modelo v2, la nota de `party.color` |
| `test_docs_ingesta_and_agents_gold` | R17 | subcadenas en `docs/ingestor/ingesta.md`, `ingestor/AGENTS.md`, `.agents/architecture.md` y `web/AGENTS.md` |
| `test_drawio_gold_page` | R15 | página «Gold»; contenedor por vista; columnas esperadas como prefijo de cada fila |

Con la fixture `db` (esquemas de test; los fixtures de datos se insertan por ORM y las vistas se consultan con `select(Base.metadata.tables["gold.<vista>"])`, que se traduce al esquema de test):

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_election_summary_aggregates` | R5, R11 | una fila por elección; censo/nulos/blancos/candidaturas/válidos/votantes y `turnout_pct` con la semántica congelada |
| `test_result_by_area_grain_and_levels` | R6 | una fila por (elección, nivel, área, partido); columnas de área nulas donde no aplican; `level` del vocabulario cerrado |
| `test_result_by_area_pct_over_valid_votes` | R6, R11 | `pct` = votos / (candidaturas + blancos) del área × 100 a 2 decimales; NULL con denominador 0 |
| `test_result_by_station_identity_and_pct` | R7 | identidad de mesa + `pct` por mesa (candidaturas + blancos de la mesa) |
| `test_station_turnout_derived_voters` | R8, R11 | `voters` = candidaturas + blancos + nulos; `turnout_pct`; mesa sin votos → `candidature_votes` 0 |
| `test_poll_flat_shape_and_nulls` | R9 | una fila por resultado; fechas/muestra/turnout/`pct`/escaños NULL tal cual (la vista no filtra) |
| `test_poll_trend_ordered_by_fieldwork` | R10 | `poll_date` = fin (o inicio) del trabajo de campo; filas ordenadas; `pg_get_viewdef` contiene `ORDER BY` |

De solo lectura contra la base real (skip sin Postgres, sin vistas o sin datos — patrón de la feature 11):

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_live_gold_views_match_models` | R1, R3 | las seis vistas existen en `gold` y sus columnas reflejadas igualan las de `models.py` |
| `test_live_poll_brands_colored` | R22 | ninguna marca de sondeos con `poll_result` tiene `color` nulo |

## Decisiones

- **Una vista por consulta del frontend** (seis en total): la web no compone ni agrega; elige la vista y filtra por `election_id`/`level`/`municipality_ine_code`/`polling_station_id`/`party_slug`. El contrato (R13) asigna pantalla ↔ vista.
- **`result_by_area` con columna `level`** (en vez de una vista por nivel): un solo artefacto para el drill nacional → CCAA → provincia → municipio y un solo sitio donde arreglar la semántica; el front siempre filtra por nivel y elección. El planner descarta las ramas no filtradas (`One-Time Filter: false` medido).
- **Joins repetidos por rama en `result_by_area`, sin CTE compartida**: una CTE usada por las cuatro ramas se materializa y el filtro de la web (`election_id = …`) no entra en la agregación — medido: 3,1 s con CTE frente a <0,3 s con los joins inline (2023, filtro por nivel). Documentado por si alguien "limpia" la duplicación.
- **Porcentaje sobre votos válidos** (candidaturas + blancos), no sobre votantes ni sobre candidaturas: es la base estándar de publicación y la misma que usan censo/participación de `silver`; `blank_votes` vive en `turnout`, de ahí el `area_blank`.
- **`poll_date` = `coalesce(fieldwork_end, fieldwork_start)`**: fin del trabajo de campo como fecha de referencia de la tendencia; el fallback evita perder sondeos con rango incompleto (hoy: 0 nulos).
- **`poll_flat` y `poll_trend` separadas**: la plana alimenta la tabla (columnas completas, sin orden contractual); la de tendencia es la consulta del gráfico — una sola fila ordenada por serie y la fecha ya resuelta.
- **El SQL vive en `gold.py`** (no en la migración): la migración y la fixture de tests consumen la misma fuente; el test de sincronía evita divergencias.
- **Vistas fuera del autogenerate** (`include_object`): autogenerate no modela vistas y sin el filtro `alembic check` pediría `create_table`. El precio: `alembic check` no vigila el SQL de las vistas; lo cubren los tests (metadata ↔ vista reflejada) y los tres sitios de la regla de oro.
- **`Table` de Core, sin clases ORM**: las vistas son contrato de lectura para la web (que no usa SQLAlchemy); una clase mapeada invitaría a escribir por ahí y añade superficie sin uso.
- **`party_color` nullable de punta a punta**: la curación es incremental (ficha a ficha); NULL es un estado válido y la web tiene su color por defecto.
- **Color solo desde el catálogo, aplicado por el resolver**: una única fuente de identidad de marca (la 12) y el bucle de curación ya definido (editar catálogo → recargar). No se hardcodea en las vistas ni se crea tabla nueva.

## Alternativas descartadas

1. **Una vista por nivel (`result_national`, `result_by_community`, …)**: cuatro definiciones casi idénticas y cuatro migraciones que mantener para el mismo contrato; la columna `level` no impide el pushdown (medido). Se descarta por duplicación.
2. **`gold` con tablas materializadas (refresh por job)**: el volumen local (6 M de votos) responde en décimas de segundo con filtro; el refresh añade un job, un estado y una ventana de datos viejos que nadie pide. Cuando el volumen lo exija, se muda a `MATERIALIZED VIEW` con su migración.
3. **Calcular porcentajes en la web** (o exponer solo votos): el acceptance los quiere solo en `gold`; y descentralizarlos abriría dos definiciones de «válidos».
4. **Vistas definidas solo en la migración** (sin `models.py`/`gold.py`): rompería la regla de oro (los tres sitios) y la trazabilidad modelo ↔ vista que comprueban los tests.
5. **`alembic-utils` (`op.create_view`)**: dependencia nueva sin consentimiento (conventions.md) para algo que `op.execute` + `include_object` cubren sin más.
6. **Agregar participación por área en una séptima vista**: fuera del MVP; el detalle de mesa ya la tiene y añadirla es una vista más cuando se pida.
7. **Repartir escaños (D'Hondt) en `gold`**: no está en el acceptance y la fuente no lo publica como hecho; los escaños que hay son los proyectados por los sondeos (`poll_result`).
8. **Colores por `CASE`/tabla dentro de `gold`**: la curación no vive en SQL ni en una tabla nueva; el catálogo ya es la fuente de identidad (feature 12) y el resolver el mecanismo (features 13–14).
9. **Copiar el SQL de las vistas a la fixture de test en vez de parametrizar `view_ddl()`**: dos verdades que divergen en silencio; los tests ejercitarían SQL que no es el desplegado.

## Interfaz para la feature 16 (web)

- **Lee `gold.*` con SELECT en servidor** (Server Components), con el rol de solo lectura que creará su propia migración; nunca escribe, nunca lee `silver`, nunca mueve credenciales al cliente.
- **Pantallas ↔ vistas**: las de la tabla de `docs/db/gold.md` (R13). El contrato está cerrado: la web no redefine columnas ni semántica; si falta un dato, se añade una vista aquí (nueva migración + ERD + doc).
- **Particularidades**: `party_color` y `municipality_name` pueden ser NULL (fallback en la web); `pct`/`seats_*` de sondeos pueden ser NULL (hueco en la serie); `poll_trend` ya llega ordenada; `election_summary` da la última general con `order by election_date desc limit 1`.
- **La feature 17** (README/atribución) reutilizará `poll_flat.revision_id`/`source` para la atribución CC BY-SA.
