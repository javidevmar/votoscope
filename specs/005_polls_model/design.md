# Diseño — `polls_model`

Feature 5. Plan de iniciativa: [`.agents/plans/polls-wikipedia.md`](../../.agents/plans/polls-wikipedia.md), § «Modelo (silver)». Solo modelo: sin parser, sin loader y sin CLI (features 6–9).

## Archivos

| Acción | Archivo |
| --- | --- |
| modificar | `ingestor/src/ingestor/models.py` — tres clases nuevas en la sección silver |
| crear | `ingestor/alembic/versions/<rev>_polls_model.py` — autogenerada |
| modificar | `docs/db/schema.drawio` — páginas «Bronze polls» y «Silver polls» |
| modificar | `.agents/data-model.md` — regla de páginas y tablas del modelo v2 |
| crear | `ingestor/tests/test_polls_model.py` — metadata (R1–R10) + sincronización de docs (R13–R15) |

Sin dependencias nuevas (stack aprobado), sin excepciones nuevas, sin firmas de funciones/CLI. Los nombres públicos nuevos son las clases `Pollster`, `Poll`, `PollResult` y los constraints `poll_turnout_range` y `poll_result_pct_range`.

## Los tres sitios de la regla de oro

### 1. ERD — `docs/db/schema.drawio`

- Página **«Silver polls»** (nueva):
  - `pollster`: `id` PK, `name`, `slug` UK(60).
  - `poll`: `id` PK, `pollster_id` FK→`pollster.id`, `source`, `election_type`, `election_id` FK→`election.id` (nullable), `fieldwork_start`, `fieldwork_end`, `sample_size`, `turnout` (CHECK 0–100), `revision_id`.
  - `poll_result`: `id` PK, `poll_id` FK→`poll.id` (indexada), `party_id` FK→`party.id` (indexada), `pct` (CHECK 0–100), `seats_min`, `seats_max`, UK (`poll_id`, `party_id`).
  - `party` y `election` como cajas **atenuadas** (solo referencia, para trazar las FK).
- Página **«Bronze polls»** (nueva): flujo del sondeo — nodo fichero `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext` → `bronze.ingestion` como caja de referencia atenuada (la tabla se dibuja en la página «Bronze»; no hay tablas nuevas en bronce).
- Construir/validar con la skill `database-erd-drawio` (contenedores de tabla con columna de constraints PK/FK/UK, patas de crow's foot enganchadas a la fila). Las páginas «Bronze» y «Silver» existentes no se tocan.

### 2. Modelos — `ingestor/src/ingestor/models.py`

Tres clases al final de la sección silver, con el patrón del fichero (`Mapped[...]`, `ClassVar[TableArgs]`, `{"schema": "silver"}`, CHECKs con nombre según la convención existente `election_scope_at_most_one`):

```python
class Pollster(Base):
    """Polling firm signing a poll (extracted from the source literal)."""

    __tablename__ = "pollster"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(60), unique=True)


class Poll(Base):
    """One opinion poll from the Wikipedia snapshot."""

    __tablename__ = "poll"
    __table_args__: ClassVar[TableArgs] = (
        CheckConstraint("turnout >= 0 AND turnout <= 100", name="poll_turnout_range"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pollster_id: Mapped[int] = mapped_column(ForeignKey("silver.pollster.id"))
    source: Mapped[str] = mapped_column(Text)  # header literal, e.g. SocioMétrica/El Español
    election_type: Mapped[str] = mapped_column(String(20))  # congress | ...
    election_id: Mapped[int | None] = mapped_column(ForeignKey("silver.election.id"))
    fieldwork_start: Mapped[date | None] = mapped_column(Date)
    fieldwork_end: Mapped[date | None] = mapped_column(Date)
    sample_size: Mapped[int | None]
    turnout: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    revision_id: Mapped[int] = mapped_column(BigInteger)


class PollResult(Base):
    """Percentage and seat projection of one party in one poll."""

    __tablename__ = "poll_result"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("poll_id", "party_id"),
        CheckConstraint("pct >= 0 AND pct <= 100", name="poll_result_pct_range"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("silver.poll.id"), index=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("silver.party.id"), index=True)
    pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    seats_min: Mapped[int | None]
    seats_max: Mapped[int | None]
```

Imports nuevos: `BigInteger` y `Numeric` (de `sqlalchemy`), `Decimal` (de `decimal`); `CheckConstraint`, `Date`, `ForeignKey`, `String`, `Text` y `UniqueConstraint` ya están importados.

### 3. Migración — `ingestor/alembic/versions/`

- `uv run alembic revision --autogenerate -m "polls model"` desde `ingestor/` (`env.py` ya toma `DATABASE_URL` e `include_schemas`).
- Revisar la migración: solo debe crear las tres tablas; el esquema `silver` ya existe, así que no requiere `CREATE SCHEMA IF NOT EXISTS`. Nunca DDL a mano; la migración aplicada no se edita.
- `uv run alembic upgrade head` y `uv run alembic check` sin drift contra el Postgres de `:5434`. La CI del ingestador ya ejecuta ambos pasos.

## Decisiones

- **Nullabilidad de `pct`/`seats`/`turnout`/fechas/muestra**: el wikitexto publica `?`, `–` y `<2.0`; el modelo los admite como NULL (los mapeará la feature 8).
- **`revision_id` BIGINT**: los `revid` de Wikipedia crecen y superan el rango de int4; BIGINT fija el guard de recarga de la feature 9.
- **`election_type` sin CHECK de vocabulario**: mismo vocabulario que `election.type` (`congress`), que tampoco lo restringe.
- **Índices**: `poll_result.poll_id` y `poll_result.party_id` indexados (consulta por sondeo y por partido); `poll` sin índices extra (tabla pequeña; el guard usa `max(revision_id)`).
- **No se guardan**: `Lead` (derivable), notas al pie y referencias (viven en el bronce) ni la fila del resultado de 2023 (vive en `vote`). Sin CHECK `seats_min <= seats_max`: la fuente publica rangos y no está en acceptance (YAGNI).
- **R11–R12 se verifican por comando, no por pytest**: `alembic check` es el verificador real del drift y ya corre en CI e `init.sh` §5; duplicarlo en pytest acoplaría la suite a una base migrada. R13–R15 sí llevan test (parseo de los docs con `xml.etree.ElementTree`).

## Alternativas descartadas

1. **Todo en la página ERD «Silver»** — mezcla dominios (elecciones vs sondeos) y agranda una página ya densa; el plan fija páginas por dominio.
2. **Resultados por partido en JSONB dentro de `poll`** — pierde la FK a `party`, el UK (`poll_id`, `party_id`) y los CHECK de rango; complica el gold de la feature 15.
3. **`election_id` NOT NULL con una elección ficticia de 2026** — inventa un dato que no existe (decisión 4 del plan); nullable + `election_type` es la representación honesta.
4. **Histórico de revisiones en silver** (una fila por `revision_id`) — silver refleja el último snapshot (decisión 3 del plan); el histórico ya está en bronce.
5. **Migración escrita a mano o DDL directo** — prohibido por la regla de oro: `models.py` → autogenerate → migración.
