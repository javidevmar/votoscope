# Diseño — `source_norm`

Feature 18 de [`feature_list.json`](../../feature_list.json) (iniciativa `polls-wikipedia`). Alcance: (a) el adaptador extrae del literal de firma tres papeles —encuestadora, medio y reestimador—, (b) `silver.poll` los representa con dos columnas de texto nulables (regla de oro completa: ERD ↔ `models.py` ↔ migración), (c) el loader los escribe con recarga idempotente y (d) los documentos de la fuente, del ingestador y del modelo quedan al día.

Estado verificado al redactar (2026-10-18, Postgres local `:5434`): 28 `pollster`, 575 `poll`, 43 literales de firma distintos (§«Inventario de literales reales»); `silver.poll.media`/`reestimator` no existen aún. El código de partida es el de las features 8 y 9 (`polls/adapters/wikipedia_polls.py` con `_pollster_name`, `polls/loaders/polls.py` con `load_polls`).

## Orden y convivencia con otras features

- **Llega después de la 14** (`party_polls`, ya en `spec_ready`): cuando se implemente esta feature, el adaptador ya no tendrá `PARTY_COLUMNS`/`PartyColumn` (resolverá rótulos contra `data/party_catalog.toml` con `Catalog.lookup`) y el loader usará `PartyResolver`. **La 18 no toca la resolución de partidos**: solo añade la descomposición del literal de firma (`_read_row`) y dos claves al `insert(Poll)` (`load_polls`). El punto de sutura con la 14 es `_read_row` (aquí se añade `parse_signature`) y el diccionario `poll_rows` del loader.
- **La 13** (`party_reload`, `spec_ready`) no toca estos ficheros de sondeos salvo el import de `slugify`; sin conflicto.
- **La 15** (`delivery_gold`, `pending`) puede crear la vista `gold` de sondeos antes de esta feature. Si al implementar ya existe, la vista puede exponer `media`/`reestimator` si el front lo pide, pero **no es acceptance de esta feature** y no se toca `gold` aquí. Si la 15 aún no existe, no hay nada que hacer.
- **Migración**: la 18 es la primera feature de la iniciativa en tocar el esquema desde la 5 (la 13/14 declaran «no toca el modelo»). La migración se autogenera sobre el `head` vigente en el momento de implementar (no se fija aquí un `down_revision`).

## Estado observado del código (extracto relevante)

- `polls/adapters/wikipedia_polls.py`: `PollRow(source, pollster_name, fieldwork_start, fieldwork_end, sample_size, turnout, results)`; `_pollster_name(source)` = `re.split(r"[/(]", source, maxsplit=1)[0].strip()`; `parse_polls`/`poll_tables` públicos; módulo sin red, sin disco (tras la 14, el catálogo de partidos es la única lectura: `load_catalog()`) y sin base de datos.
- `polls/loaders/polls.py`: `load_polls` construye `poll_rows` (un dict por `PollRow`) e inserta en bloque con `insert(Poll).returning(Poll.id, sort_by_parameter_order=True)`; `_validate` exige firma no vacía (`row.source` o `row.pollster_name`).
- Tests que leen la firma: `test_wikipedia_polls.py::test_pollster_name_extraction`, `::test_real_cis_block`, `::test_real_head_first_rows`; `test_polls_load.py::test_cli_registers_and_loads`; `test_polls_model.py::test_silver_polls_page_has_complete_tables` (enumera las columnas del drawio).

## Decisión

- **Extracción en el adaptador, como regla de la fuente** (feature 8: la sección/cabecera es del adaptador): una función pura `parse_signature(source) -> Signature` que aplica las reglas de §«Reglas de extracción». El `source` literal no se toca (R7).
- **Representación en `silver` con dos columnas de texto nulables** en `poll` (`media`, `reestimator`), no con tablas de identidad: hoy ningún consumidor necesita identidad de medio/reestimador (la vista `gold` de la 15 ni la pide), la idempotencia de la recarga es trivial (las columnas viajan con la fila de `poll`, que ya se reemplaza entera) y se evita crear filas de identidad para literales ambiguos (`JM`, `PSOE`). La identidad de medio/reestimador, si hiciera falta, es una curación futura (tabla + alias), no de esta feature.
- **El reestimador es el paréntesis final** (`CIS {{smaller|(X)}}` → `X`); el medio es el tramo tras la primera barra. Se guardan literales, **sin fusionar alias** (`CIS (JM)` ≠ `CIS (Jaime Miquel)`) ni reclasificar comisionantes (`SocioMétrica/PP` → medio `PP`).
- **Sin cambio de `poll.source`**: sigue siendo el literal completo (R7); el cotejo de la 11 y la licencia no se tocan.

## Reglas de extracción

`parse_signature` (pura; `strip` en cada parte):

1. **Paréntesis final** `^(?P<head>.+?)\s*\((?P<inner>[^()]*)\)$`: `head` es la encuestadora provisional, `inner` el reestimador. Si `inner` queda vacío → warning y reestimador nulo (R5). (Solo el CIS lo usa hoy.)
2. **Primera barra** sobre el texto restante (o el literal completo si no hubo paréntesis): `partition("/")` → encuestadora = tramo izquierdo (`strip`), medio = tramo derecho (`strip`) o nulo si vacío, con warning `signature part is empty` (R5).
3. **Sin separadores**: el literal completo es la encuestadora; medio y reestimador nulos (R3).
4. La encuestadora vacía (p. ej. `/Medio`, `()`) no se inventa: `pollster_name` queda vacío y la validación del loader (feature 9, R17) aborta la carga como hoy; el adaptador no la parchea.

Precedencia y determinismo (R4): primero el paréntesis (si cierra el literal), después la barra sobre el resto. Un literal como `Firm (X)/Media` (no existe en la página) no encaja en el paréntesis final: la barra parte el literal completo (`Firm (X)` + `Media`) — documentado como no soportado; una deriva así avisa por el camino normal de la feature 8 si el resultado rompe las validaciones.

### Inventario de literales reales (43; tres snapshots locales, 2026-10-29)

Inventario completo de `silver.poll.source` (la columna «Encuestadora» es el valor esperado de `pollster_name`; «—» = nulo). Es la tabla de casos del test del adaptador (R15).

| Literal (`poll.source`) | Encuestadora | Medio | Reestimador |
| --- | --- | --- | --- |
| `40dB/Prisa` | 40dB | Prisa | — |
| `Ateneo del Dato` | Ateneo del Dato | — | — |
| `Ateneo del Dato/elDiario.es` | Ateneo del Dato | elDiario.es | — |
| `Celeste-Tel/Onda Cero` | Celeste-Tel | Onda Cero | — |
| `CIS` | CIS | — | — |
| `CIS (Ateneo del Dato)` | CIS | — | Ateneo del Dato |
| `CIS (Demócrata)` | CIS | — | Demócrata |
| `CIS (Jaime Miquel)` | CIS | — | Jaime Miquel |
| `CIS (JM)` | CIS | — | JM |
| `CIS (Logoslab)` | CIS | — | Logoslab |
| `CIS (Opina 360)` | CIS | — | Opina 360 |
| `CIS (SocioMétrica)` | CIS | — | SocioMétrica |
| `CIS (Sondaxe)` | CIS | — | Sondaxe |
| `CIS (Target Point)` | CIS | — | Target Point |
| `Cluster17/Agenda Pública` | Cluster17 | Agenda Pública | — |
| `Data10/Okdiario` | Data10 | Okdiario | — |
| `Demoscopia y Servicios/esRadio` | Demoscopia y Servicios | esRadio | — |
| `DYM/Henneo` | DYM | Henneo | — |
| `EM-Analytics/Electomanía` | EM-Analytics | Electomanía | — |
| `GAD3/ABC` | GAD3 | ABC | — |
| `GAD3/Mediaset` | GAD3 | Mediaset | — |
| `GAD3/Vocento` | GAD3 | Vocento | — |
| `GESOP/Prensa Ibérica` | GESOP | Prensa Ibérica | — |
| `Hamalgama Métrica/Vozpópuli` | Hamalgama Métrica | Vozpópuli | — |
| `IMOP/El Confidencial` | IMOP | El Confidencial | — |
| `InvyMark/laSexta` | InvyMark | laSexta | — |
| `Ipsos/La Vanguardia` | Ipsos | La Vanguardia | — |
| `KeyData/Público` | KeyData | Público | — |
| `More in Common` | More in Common | — | — |
| `NC Report/La Razón` | NC Report | La Razón | — |
| `ODEC/Mediaflows–UV` | ODEC | Mediaflows–UV | — |
| `Opina 360/Antena 3` | Opina 360 | Antena 3 | — |
| `Opina 360/Telecinco` | Opina 360 | Telecinco | — |
| `PSOE` | PSOE | — | — |
| `Sigma Dos/Antena 3` | Sigma Dos | Antena 3 | — |
| `Sigma Dos/El Mundo` | Sigma Dos | El Mundo | — |
| `Simple Lógica/elDiario.es` | Simple Lógica | elDiario.es | — |
| `SocioMétrica/El Español` | SocioMétrica | El Español | — |
| `SocioMétrica/PP` | SocioMétrica | PP | — |
| `Sondaxe/La Voz de Galicia` | Sondaxe | La Voz de Galicia | — |
| `Sumar` | Sumar | — | — |
| `Target Point/El Debate` | Target Point | El Debate | — |
| `Winston/Artículo14` | Winston | Artículo14 | — |

Notas del inventario: `ODEC/Mediaflows–UV` lleva **en dash** (`–`, U+2013) en el medio; `SocioMétrica/PP` es un sondeo encargado por un partido (el medio/comisionante se guarda literal); `Ateneo del Dato` aparece solo, como medio (`…/elDiario.es`) y como reestimador del CIS; `Target Point`, `Sondaxe`, `SocioMétrica` y `Opina 360` aparecen como encuestadora propia y como reestimadores del CIS; `Demócrata`, `Logoslab` y `Jaime Miquel` existen hoy solo como reestimadores.

**El inventario no es cerrado.** Los tres snapshots locales producen la misma unión de 43 literales, pero el bronce puede contener revisiones anteriores o futuras con firmas nuevas: el inventario se construye con la unión de todos los `*.wikitext` de `data/raw/polls/**` (recorriendo las tablas con el lexer y leyendo la celda de firma) y se regenera cuando aparezca un fetch nuevo. Los literales históricos que ya no estén en la página actual también entran en la tabla y en el test. En el código no hay lista blanca: la tabla vive solo en los tests (R15, R20).

## Firmas nuevas — `polls/adapters/wikipedia_polls.py`

```python
@dataclass(frozen=True)
class Signature:
    """Roles of a signature literal: firm, media and reestimator."""

    pollster_name: str
    media: str | None
    reestimator: str | None


def parse_signature(source: str) -> Signature:
    """Signature literal as its three roles (firm / media / reestimator)."""
```

- `PollRow` gana `media: str | None` y `reestimator: str | None` (después de `pollster_name`).
- `_read_row` calcula `signature = parse_signature(source)` y rellena `source`, `pollster_name`, `media`, `reestimator`.
- `_pollster_name(source)` desaparece; su contrato (texto anterior a la primera `(` o `/`) queda cubierto por `parse_signature(...).pollster_name` para los 43 literales reales (mismo resultado).
- `_PARENTHESISED = re.compile(r"^(?P<head>.+?)\s*\((?P<inner>[^()]*)\)$")` (nuevo). Sin `re` nuevo (ya importado).

### Warnings (subcadenas estables para `caplog`)

| Subcadena | Caso | R |
| --- | --- | --- |
| `signature part is empty` | medio o reestimador vacío (`Firm/`, `CIS ()`) | R5 |

Sin logs INFO (convención de los parsers del repo).

## Los tres sitios de la regla de oro

### 1. ERD — `docs/db/schema.drawio`, página «Silver polls»

- En la caja `poll` (`sp_poll`), dos filas nuevas **después de `source`** (`sp_poll_source_row`): `sp_poll_media_row` (`media text`, flag `NULL`) y `sp_poll_reestimator_row` (`reestimator text`, flag `NULL`), con el mismo estilo de las filas existentes (`shape=partialRectangle`, columna de constraints vacía, texto a la izquierda, flag itálico).
- Desplazar las filas siguientes +60 en `y` (`election_type` 120→180, `election_id` 150→210, `fieldwork_start` 180→240, `fieldwork_end` 210→270, `sample_size` 240→300, `turnout` 270→330, `revision_id` 300→360) y la altura de la caja `sp_poll` 330→390.
- Construir/validar con la skill `database-erd-drawio`; las demás páginas y cajas no se tocan.

### 2. Modelos — `ingestor/src/ingestor/models.py`

```python
class Poll(Base):
    ...
    source: Mapped[str] = mapped_column(Text)  # header literal
    media: Mapped[str | None] = mapped_column(Text)  # commissioner/media literal
    reestimator: Mapped[str | None] = mapped_column(Text)  # alternative projection author
    election_type: Mapped[str] = mapped_column(String(20))  # congress | ...
```

Sin CHECK ni índice (texto libre, tabla pequeña); `Text` ya está importado.

### 3. Migración — `ingestor/alembic/versions/`

- `uv run alembic revision --autogenerate -m "poll source roles"` desde `ingestor/` (env.py toma `DATABASE_URL`).
- Revisar: solo dos `op.add_column("poll", sa.Column(..., sa.Text(), nullable=True), schema="silver")`; no hay `CREATE SCHEMA` (existe desde la 2).
- `uv run alembic upgrade head` y `uv run alembic check` (R10). La migración **no** rellena datos: las filas ya cargadas quedan con `NULL` hasta la recarga (`ingest-polls --force`, §«Evidencia»); un backfill en SQL duplicaría las reglas de la fuente (descartado).

## Loader — `polls/loaders/polls.py`

Solo `load_polls`: cada dict de `poll_rows` gana dos claves.

```python
poll_rows = [
    {
        "pollster_id": pollster_ids[...],
        "source": row.source,
        "media": row.media,
        "reestimator": row.reestimator,
        "election_type": ELECTION_TYPE,
        ...
    }
    for row in rows
]
```

Idempotencia (R14): sin código nuevo. `poll`/`poll_result` se reemplazan enteros en cada carga (`delete` + `insert`), así que recargar el mismo snapshot con `--force` reproduce el mismo contenido; los saltos de la feature 9 (`processed` y guard de revisión) son la razón de que haga falta `--force` tras migrar. `_validate` no cambia (la firma sigue siendo `source` + `pollster_name`).

## Tests

### `test_wikipedia_polls.py` (modificar)

| Test | Qué fija | Cubre |
| --- | --- | --- |
| `test_parse_signature_real_literals` (parametrizado con la unión del inventario de §«Inventario de literales reales») | los 43 literales de los tres snapshots locales → `(pollster_name, media, reestimator)` | R1, R2, R3, R6, R15 |
| `test_parse_signature_unknown_literal` | un literal sintético no inventariado (`Encuestadora Nueva/Medio Nuevo`) se descompone por las reglas generales, sin lista blanca | R20 |
| `test_parse_signature_combined_and_empty_parts` | `Firm/Media (X)` → tres papeles; `Firm/` y `CIS ()` → nulo + warning `signature part is empty` | R4, R5 |
| `test_pollster_name_extraction` (actualizado) | `SocioMétrica/El Español` → medio `El Español`; `CIS (Target Point)` → reestimador `Target Point`; `More in Common` → nulos | R1–R3, R6 |
| `test_real_cis_block` / `test_real_head_first_rows` (ampliados) | reestimadores `Opina 360`/`Ateneo del Dato`/None del bloque CIS; medios `El Español`/`El Debate` de las filas reales; `source` literal intacto | R7 |

Sin red: los literales van como tabla inline (la unión del bronce, congelada en el test) y las fixtures `real_2026_head.wikitext` ya existen.

### `test_polls_load.py` (modificar)

| Test | Qué fija | Cubre |
| --- | --- | --- |
| `test_cli_registers_and_loads` (ampliado) | `poll.media`/`poll.reestimator` tras la carga: `Alpha/Medio` → `Medio`/NULL; `CIS (Target Point)` → NULL/`Target Point` | R13 |
| `test_reload_roles_is_idempotent` (nuevo) | dos cargas `--force` del mismo snapshot: mismos tríos `(source, media, reestimator)` por fila y mismo conteo en `poll`, sin duplicados | R14 |
| `test_docs_ingesta` (ampliado) | subcadenas `media`, `reestimator` | R18 |
| `test_docs_ingestor_agents` (ampliado) | subcadena `reestimador` | R19 |

La fixture `load_small.wikitext` ya trae `Alpha/Medio` y `CIS (Target Point)`: no hace falta fixture nueva.

### `test_polls_model.py` (modificar)

| Test | Qué fija | Cubre |
| --- | --- | --- |
| `test_poll_source_roles_are_nullable_text` (nuevo) | `Poll.media`/`Poll.reestimator`: `Text`, nulables | R8, R9 |
| `test_silver_polls_page_has_complete_tables` (ampliado) | `media`/`reestimator` en las columnas esperadas de `poll` | R11 |
| `test_data_model_v2_describes_polls_tables` (ampliado) | subcadenas `media`/`reestimator` en el bullet de `silver.poll` | R12 |

### `test_polls_run.py` (modificar)

| Test | Qué fija | Cubre |
| --- | --- | --- |
| `test_docs_data_sources_quirks` (ampliado) | subcadenas `reestimador`, `Encuestadora/Medio` y `paréntesis` en la sección de sondeos | R17 |

Sin ficheros de fixture nuevos; sin red, sin `refs/` ni `data/raw/` (R15, R16).

## Documentos (texto pretendido)

- **`.agents/data-sources.md`**, sección «Sondeos (Wikipedia)», bullet nuevo tras «Rarezas estructurales»:

  ```markdown
  - **Papeles del literal de firma**: la columna «Polling firm/Commissioner» mezcla
    papeles y el loader los separa. `Encuestadora/Medio` (`SocioMétrica/El Español`):
    la encuestadora va a `pollster` y el medio/comisionante a `poll.media`.
    `CIS {{smaller|(Reestimador)}}` (`CIS (Target Point)`, `(Sondaxe)`, `(Logoslab)`…):
    el paréntesis del CIS es una proyección alternativa sobre sus datos brutos y su
    contenido va a `poll.reestimator`. Un literal sin separadores (`More in Common`,
    `CIS`, `PSOE`) solo tiene encuestadora: no se le inventan medio ni reestimador.
    El literal completo se conserva en `poll.source`; `CIS (JM)` y `CIS (Jaime Miquel)`
    se guardan tal cual, sin fusionar.
  ```

- **`docs/ingestor/ingesta.md`**: paso 6 de «Comportamiento de `ingest-polls`» (se añade que el adaptador separa los papeles del literal y el loader escribe `media`/`reestimator`), fila `poll` de «Qué queda en `silver`» (hoy «`source` (literal de cabecera), …») con las dos columnas nuevas, y una nota operativa: las filas cargadas antes de la migración quedan con `media`/`reestimator` nulos hasta una recarga `--force`. Se documenta también que la recarga es idempotente.
- **`.agents/data-model.md`**, bullet `silver.poll`: añadir «`media` y `reestimator` guardan el medio/comisionante y el autor de la proyección alternativa cuando el literal de la firma los distingue (nulos si no)».
- **`ingestor/AGENTS.md`**, bullet de `src/ingestor/polls/`: el adaptador documenta «cabecera —con la separación de encuestadora/medio/reestimador del literal de firma—».

Subcadenas estables que fijan los tests: `media`, `reestimator`, `reestimador`, `Encuestadora/Medio`, `paréntesis` (y ninguna aserción sobre el texto completo).

## Evidencia (operativa, no acceptance)

Tras implementar, con los tests verdes, desde `ingestor/` contra el Postgres local:

1. `uv run alembic upgrade head` y `uv run alembic check`.
2. `uv run ingestor ingest-polls --force` (recarga del snapshot local; exit 0; los warnings esperados son de la fuente, no de esta feature).
3. SQL de comprobación: conteo de papeles por forma y spot-check de la tabla del inventario.

   ```sql
   SELECT count(*) FILTER (WHERE media IS NOT NULL) AS con_medio,
          count(*) FILTER (WHERE reestimator IS NOT NULL) AS con_reestimador,
          count(*) FILTER (WHERE media IS NULL AND reestimator IS NULL) AS solo_encuestadora
   FROM silver.poll;

   SELECT source, media, reestimator FROM silver.poll
   WHERE source IN ('CIS (Target Point)', 'SocioMétrica/El Español', 'More in Common')
   ORDER BY source;
   ```

4. Registrar la salida y los conteos en `progress/impl_source_norm.md` (convención del arnés).

## Decisiones

- **Extracción en el adaptador**: es una regla de la fuente (feature 8: cabecera y limpieza); el loader solo persiste. Reimplementarla en el loader duplicaría la regla.
- **Columnas de texto, no identidades**: sin consumidor que pida identidad de medio/reestimador; la idempotencia es trivial y «sin inventar» (R3) se cumple por construcción. La curación de alias (`JM` → `Jaime Miquel`) sería una feature futura con su catálogo.
- **Paréntesis final = reestimador**: hoy solo el CIS lo usa; el literal se guarda tal cual (incluido `JM`).
- **Sin backfill en la migración**: un backfill en SQL duplicaría las reglas de extracción; la recarga `--force` (documentada) repuebla las filas. El cron de la 10 lo haría solo si hubiera snapshot nuevo; el guard saltaría el `processed`, de ahí la nota operativa.
- **Warnings y a seguir**: un separador que deje una parte vacía avisa y deja el papel nulo; nunca excepción en el adaptador (convención de la 8).
- **Sin cambio de `pollster_id`**: los 43 literales producen la misma encuestadora que hoy; la recarga solo rellena las dos columnas nuevas.

## Alternativas descartadas

1. **Derivar medio y reestimador en `gold` con SQL desde `poll.source`** (sin tocar el esquema): duplicaría el análisis del literal en las vistas, con migraciones de vista cada vez que la fuente cambie de forma, y el acceptance pide que la recarga lo aplique. `gold` no debe parsear literales de bronce/plata.
2. **Tablas de identidad `silver.media` y `silver.reestimator` (o una sola) con FK y get-or-create**: maquinaria de identidad sin consumidor hoy; forzaría filas para literales ambiguos (`JM`) o que no ejercen de encuestadora (`Demócrata`, `Logoslab`), y complica la idempotencia (get-or-create con slugs nuevos). Si el front pide filtrar por medio, se curará entonces (tabla + alias), no ahora.
3. **Reestimador como segunda FK a `pollster` (`poll.reestimator_pollster_id`)**: confundiría papeles (un reestimador no firma el sondeo) y crearía filas `pollster` para nombres que no son encuestadoras del snapshot; además, al compartir entidad con encuestadora real (`Target Point`, `Sondaxe`, `SocioMétrica`) sugeriría una identidad que el literal no siempre da.
4. **Fusionar alias de reestimador** (`JM`/`Jaime Miquel`) con tabla de alias: inventa identidad sin evidencia; el literal es el hecho. Curación futura si hace falta.
5. **Guardar el literal solo en `poll.source` y no separar nada en plata** (todo derivado por el consumidor): es el statu quo que la feature corrige; el consumidor no debe repetir las reglas.
6. **Sustituir `poll.source` por las partes** (`pollster`/`media`/`reestimator` sin literal): se perdería la trazabilidad con la página y el cotejo de la 11; `source` se conserva (R7).
7. **Backfill de las columnas en la migración** (SQL con `split_part`/regex): duplicaría las reglas del adaptador y las congelaría en SQL; mejor una recarga documentada y verificable.

## Riesgos y notas

- **Sutura con la 14**: el test `test_module_is_stdlib_only_and_pure` de la 14 admite `ingestor.parties` en los imports; la 18 no añade imports nuevos (solo `re`, ya presente).
- **Filas antiguas**: hasta la recarga `--force`, `media`/`reestimator` están nulos; no es un dato perdido (`poll.source` lo tiene) y la recarga es idempotente.
- **`CIS (JM)`**: se guarda `JM` (no `Jaime Miquel`); si una curación futura quiere fusionarlos, será con alias explícitos.
- **Nombres con en dash** (`Mediaflows–UV`): el `strip` no toca caracteres internos; el test del inventario lo fija.
- **Otros procesos/sondeos** (Senado, autonómicas, otros años): las reglas son de la fuente Wikipedia en inglés; un literal nuevo sin separadores cae en R3 sin inventar.
- **Inventario histórico y futuros fetchs**: la tabla de 43 es la unión de los tres snapshots locales; si un fetch nuevo (o una revisión antigua recuperada) introduce un literal, se regenera la tabla desde `data/raw/polls/**` y se añade al test. El código no cambia por un literal nuevo (R20).
