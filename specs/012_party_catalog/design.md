# Diseño — `party_catalog`

Feature 12 de [`feature_list.json`](../../feature_list.json) (iniciativa `party-norm`), redactada absorbiendo el diseño de la iniciativa. Alcance: el catálogo `src/ingestor/data/party_catalog.toml` (fichas de marca con `name` y `aliases`), el módulo `src/ingestor/parties.py` (normalización, catálogo y resolución `catálogo → nombre existente → alta con warning`) y sus tests. **No integra los loaders**: `_resolve_parties` de elecciones y de sondeos pasan por el resolver en las features 13 y 14.

**No toca el modelo de datos**: sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic (la regla de oro no aplica); `party` y `party_election` valen tal cual y `party.color` sigue fuera (se curará con `gold`). Sin dependencias nuevas (`tomllib` es stdlib). Sin excepciones nuevas (`IngestError`). Sin CLI.

## Diagnóstico (absorbido)

- `silver.party` tiene **547 filas** para 13 procesos (387 de un solo proceso, 160 en varios). La identidad se deriva de las siglas de la cabecera nacional del `03` (`_resolve_parties`, slug de las siglas): la misma marca con otra grafía en otro año crea fila nueva.
- **27 grupos** de filas con el mismo nombre salvo puntuación: `B.N.G.`/`BNG`, `P.P.`/`PP`, `P.S.O.E.`/`PSOE`, `C's`/`Cs`, `I.U.`/`IU`, `P.C.P.E.`/`PCPE`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `D.N.`/`DN`, `A.u.N.`/`AUN`… (55 filas en total). No es solo histórico: en el 2023 del MVP (59 filas de `party`), BNG, UPL y FIA están en la fila punteada —el BNG alterna (limpia en 1986–2004, 2011 y 2019; punteada en 2008 y 2023), UPL va limpio en 1993–2019 y punteado en 2023, y FIA limpio en 2019 y punteado en 2023—: la web partiría las series justo en el año que enseña.
- Grafías **distintas** que ya son curación, no puntuación: familia Podemos (`podemos`, `podemos-iu-…`, `unidas podemos`), verdes (`lv`, `lve`, `lv-gv`, `verdes`), `fe-de-las-j`/`fe-de-las-jons`/`fe-jons`, `na`/`na-bai`, `erc`/`esquerra`/`erc-catsi`…
- **Sondeos**: 13 de las 15 etiquetas de `PARTY_COLUMNS` ya resuelven a slugs existentes (`pp`, `psoe`, `vox`, `sumar`, `erc`, `jxcat-junts`, `eh-bildu`, `eaj-pnv`, `bng`, `cca`, `u-p-n`, `adelante-andalucia`, `podemos`); `salf` y `alianca-cat` se crearían del literal del adaptador. Sin una identidad común, la web no puede unir sondeos y resultados por partido.

## Decisión

- **Catálogo versionado en el paquete**: `src/ingestor/data/party_catalog.toml` — por slug canónico, `name` (la grafía legible, como hasta ahora) y `aliases` (grafías que no coincidan por normalización). Es curación, no descarga, así que va en git; TOML leído con `tomllib` de la stdlib. El fichero vive dentro del paquete (`src/ingestor/data/`), de modo que `Path(__file__).parent / "data" / "party_catalog.toml"` lo encuentra en instalación editable y en el wheel.
- **Resolución compartida** en `src/ingestor/parties.py`, usada por el loader de elecciones (feature 13) y, cuando nazca, el de sondeos (feature 14). Para una etiqueta (siglas de cabecera del `03`, columna de la wiki): normalización → alias del catálogo → coincidencia con el nombre de un `party` existente → alta con warning.
- **Criterio de identidad**: continuidad de la **marca electoral**. Grafías de la misma marca se fusionan; coaliciones con nombre propio no (`Podemos` ≠ `Unidas Podemos` ≠ `Sumar`, aunque compartan cartel) — si el frente quiere una línea continua, se agrupa en `gold`.
- **Sin fuzzy-matching**: normalización exacta o alias explícito. **Ante la duda, no fusionar**: una serie partida se ve y se arregla con un alias + reingesta; una fusión entre marcas distintas distorsiona en silencio.
- **Sin cambio de esquema**: `silver` se recalcula reingiriendo (contrato bronce→plata); ningún fichero fuente se toca.

## Formato del catálogo

```toml
# Party catalogue: canonical electoral brands.
# Keys are canonical `silver.party` slugs; `name` and `aliases` are literal
# spellings as ingested (or as the polls source publishes them). Spellings
# that coincide after normalization need no alias.

[parties.u-p-n]
name = "U.P.N."          # slug u-p-n: la sigla ingerida iba punteada
aliases = []             # "UPN" coincide por normalización

[parties.jxcat-junts]
name = "JxCAT-Junts"     # literal ingerido
aliases = ["Junts"]      # literal del rótulo de sondeos (PARTY_COLUMNS)

[parties.salf]
name = "Se Acabó La Fiesta"  # literal del adaptador de sondeos (aún sin 03)
aliases = ["SALF"]
```

- La clave es el slug canónico (bare key de TOML: `a-z0-9-`); una tabla repetida es error de sintaxis del propio TOML (R8).
- `name` es obligatorio (R9); `aliases` es opcional y por defecto vacío (R2).
- La **clave de etiqueta** de una ficha es `normalize(name)` más `normalize(alias)` de cada alias; `lookup(label)` busca por `normalize(label)` (R3, R4).
- Integridad en carga (R5–R7): una clave no puede reclamarse desde dos fichas distintas; un alias no puede coincidir con el nombre de su propia ficha (sería redundante); ninguna clave puede quedar vacía.
- Los ejemplos de valores son ilustrativos: los literales definitivos salen de la extracción (§Curación).

## Curación

**Fichas generadas desde la BD**: los `name` y `aliases` se copian literalmente de los nombres ya ingeridos en `silver` (extracción de abajo), sin reescribirlos ni inventarlos — así ninguna etiqueta del catálogo deja de cuadrar con lo ingerido. Para cada marca partida, el canónico es uno de los `party` ingeridos (su slug y su nombre), preferentemente la grafía limpia; las grafías ingeridas que no coincidan por normalización pasan a `aliases` tal cual. Excepción: las etiquetas de sondeos que aún no tienen `03` (SALF, Aliança.cat), cuyo literal fija `PARTY_COLUMNS` (R11).

Extracción (SELECT, sobre el `silver` local con los 13 procesos):

```sql
SELECT p.slug, p.name, array_agg(DISTINCT pe.short_name ORDER BY pe.short_name) AS siglas
FROM silver.party p JOIN silver.party_election pe ON pe.party_id = p.id
GROUP BY p.id ORDER BY p.slug;
```

Volcado del alcance del 2023 (una grafía por línea para la fixture `brands_2023.txt`):

```sql
SELECT DISTINCT p.name
FROM silver.party p
JOIN silver.party_election pe ON pe.party_id = p.id
JOIN silver.election e ON e.id = pe.election_id
WHERE e.type = 'congress' AND e.date = DATE '2023-07-23'
ORDER BY 1;
```

**Alcance de la curación inicial**: las 15 etiquetas de sondeos (R10), las marcas del 2023 (~59 filas; R12) y las familias del diagnóstico (R13–R15). Los micro-partidos de un solo proceso caen por la vía normal (coincidencia por nombre, R19) sin ficha; fichas de más no estorban.

**Las decisiones de las familias** (fusionar por alias o mantener marcas separadas) son juicio de curación y se registran en el diff del catálogo: el criterio es el de §Decisión y el diff es el registro revisable. Sin fuzzy: si dos grafías no coinciden por normalización, se fusionan solo escribiendo el alias explícito.

**El bucle** (a partir de aquí lo ejecuta la feature 13 al recargar): ingerir y mirar los avisos (el warning del resolver es la cola de candidatos) → decidir (misma marca: alias; marca distinta: no se escribe nada) → editar el catálogo → `ingest --force` de los afectados (local: los 13 procesos) y borrar huérfanos → verificar con las consultas de abajo. Aplicar una curación posterior (nuevo alias, marca nueva) = editar el catálogo y reingerir los procesos afectados.

Comprobaciones tras la recarga (contexto para la feature 13; sin grupos repetidos por puntuación, las marcas clave en una sola fila, hechos intactos salvo el `party_id` de las candidaturas fusionadas):

```sql
SELECT array_agg(slug) AS slugs, count(*)
FROM silver.party
GROUP BY upper(regexp_replace(name, '[^a-zA-Z0-9]', '', 'g'))
HAVING count(*) > 1;

SELECT p.slug, p.name, count(DISTINCT pe.election_id) AS procesos
FROM silver.party p JOIN silver.party_election pe ON pe.party_id = p.id
WHERE upper(regexp_replace(p.name, '[^a-zA-Z0-9]', '', 'g'))
      IN ('BNG','UPL','FIA','CS','PP','PSOE','IU')
GROUP BY p.id ORDER BY p.slug;

DELETE FROM silver.party p
WHERE NOT EXISTS (SELECT 1 FROM silver.party_election pe WHERE pe.party_id = p.id);
```

**Riesgos anotados**: los límites de la curación (coaliciones, verdes, falange) son juicio revisable en el diff; los slugs de las filas fusionadas cambian (hoy nadie los consume: ni `gold` ni la web); el 2026 exigirá fichas nuevas (SALF, Aliança.cat y las marcas de la nueva general) antes de ingerir su `03` — aun así, el resolver avisa de cualquier alta.

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `ingestor/src/ingestor/data/party_catalog.toml` — fichas del alcance, literales de la extracción |
| crear | `ingestor/src/ingestor/parties.py` — `normalize`, `slugify`, `PartyEntry`, `Catalog`, `load_catalog`, `PartyResolver` |
| crear | `ingestor/tests/test_parties.py` — tests de R1–R28 |
| crear | `ingestor/tests/fixtures/party_catalog/brands_2023.txt` — volcado literal (R12) |
| modificar | `ingestor/src/ingestor/elections/loaders/election.py` — quitar la `slugify` local e importarla de `parties.py` (R26) |
| modificar | `ingestor/src/ingestor/polls/loaders/polls.py` — importar `slugify` de `parties.py` (R26) |

`ingestor/tests/test_rules.py` no se toca: importa `slugify` desde `election`, que sigue exponiéndola (re-exportada), y su comportamiento no cambia.

## Firmas nuevas — `src/ingestor/parties.py`

```python
CATALOG_PATH: Path = Path(__file__).parent / "data" / "party_catalog.toml"


def normalize(label: str) -> str: ...


def slugify(value: str) -> str: ...  # movida desde elections/loaders/election.py


@dataclass(frozen=True)
class PartyEntry:
    slug: str
    name: str
    aliases: tuple[str, ...] = ()


class Catalog:
    entries: tuple[PartyEntry, ...]

    def lookup(self, label: str) -> PartyEntry | None: ...


def load_catalog(path: Path = CATALOG_PATH) -> Catalog: ...


class PartyResolver:
    """Resolve labels to silver.party rows: catalogue → existing name → creation."""

    def __init__(self, parties: Iterable[Party], catalog: Catalog) -> None: ...

    def resolve(self, label: str, *, code: str | None = None) -> Party: ...
```

Detalles que fijan el contrato:

- `slugify` se mueve a `parties.py` (era privada del loader de elecciones y el de sondeos la importaba de allí): el resolver la necesita y `parties.py` no puede depender de un loader (ciclo al integrar la feature 13). `election.py` la importa y `test_rules.py` la sigue viendo. Mismo comportamiento (`"C's"`→`c-s`, `"U.P.N."`→`u-p-n`, `"  "`→`""`).
- `load_catalog` valida al cargar (R5–R9) y falla con `IngestError` (config rota = ingestión imposible): mensajes con la ruta del fichero y, según el caso, la clave en conflicto o el slug de la ficha.
- `PartyResolver` es puro: no abre sesiones ni toca la BD; recibe las filas existentes (el llamador las lee con `select(Party)`). Las filas creadas NO se añaden a ninguna sesión: el llamador hace `session.add(party)` — inofensivo si la fila ya era persistente — y `flush`.
- El resolver indexa las filas que crea, de modo que resolver dos veces la misma etiqueta (o dos etiquetas que llevan a la misma ficha) devuelve una única fila (R25).

## Algoritmo de resolución (R16–R25)

```python
def resolve(self, label, *, code=None):
    key = normalize(label)

    entry = self.catalog.lookup(label)            # (1) catálogo
    if entry is not None:
        party = self.by_slug.get(entry.slug)
        if party is None:
            party = Party(name=entry.name, slug=entry.slug)   # sin warning (R18)
            self._index(party)
        return party

    matches = self.by_name.get(key)               # (2) nombre existente
    if matches:
        return self._prefer(matches, key)

    slug = self._free_slug(slugify(label) or "party", code)   # (3) alta
    logger.warning("unknown party label: %s -> %s", label, slug)
    party = Party(name=label, slug=slug)
    self._index(party)
    return party
```

- `by_slug`: slug → fila; `by_name`: `normalize(party.name)` → filas (varias: el mismo nombre normalizado puede tener hoy dos filas).
- `_prefer`: la fila con `slug == slugify(key)` si existe; si no, la de `id` menor (R20, R21). El desempate asume filas persistidas (`id` no nulo), que es el caso real.
- `_free_slug(base, code)`: `base` si está libre; si no, `f"{base}-{code}"` cuando hay código; si no, el primer sufijo numérico libre (`-2`, `-3`, …) (R23). El slug final se recorta a 60 caracteres (límite de `party.slug`; la alta de hoy también recorta) (R22).
- Sin fuzzy: solo claves normalizadas y alias explícitos (R16); `PPX` no toca `pp`.

| Caso | Resultado | R |
| --- | --- | --- |
| Etiqueta con ficha, fila por slug existe | esa fila | R17 |
| Etiqueta con ficha, fila por slug no existe | `Party(name=ficha.name, slug=ficha.slug)` | R17, R18 |
| Sin ficha; nombre normalizado coincide con 1 fila | esa fila | R19 |
| Sin ficha; coinciden varias; una con `slug == slugify(clave)` | esa | R20 |
| Sin ficha; coinciden varias; ninguna con ese slug | la de `id` menor | R21 |
| Sin ficha ni coincidencia | `Party(name=label, slug=slugify(label)[:60])` + warning | R22, R24 |
| Slug ocupado por otra marca | sufijo `-code` o `-n` | R23 |

## Warnings (subcadenas estables para `caplog`)

| Subcadena | Caso | R |
| --- | --- | --- |
| `unknown party label` | alta sin ficha (`unknown party label: FA -> fa`) — es la señal de añadir ficha | R24 |

Sin logs INFO ni DEBUG (misma convención que los parsers del repo: solo warnings).

## Tests — `ingestor/tests/test_parties.py`

Sin red ni base de datos: el resolver se ejercita con filas `Party` transitorias (`Party(name=…, slug=…, id=…)`) y catálogos de `tmp_path`; el catálogo real se carga por la ruta por defecto. Helper para escribir un TOML de catálogo en `tmp_path`.

| Test previsto | Entrada | Cubre |
| --- | --- | --- |
| `test_normalize_matrix` | `B.N.G.`, `C's`, `P. RIOJANO`, `EH Bildu`, `Aliança.cat`, `MÁS PAÍS`, solo puntuación | R1 |
| `test_catalog_loads_toml` | TOML de `tmp_path` (varias fichas, alias opcional) | R2 |
| `test_catalog_lookup_by_name_and_alias` (incluye coincidencia por normalización) | TOML de `tmp_path` | R3 |
| `test_catalog_lookup_unknown_returns_none` | TOML de `tmp_path` | R4 |
| `test_load_catalog_rejects_duplicate_key` (alias de una ficha = nombre de otra) | TOML de `tmp_path` | R5 |
| `test_load_catalog_rejects_redundant_alias` | TOML de `tmp_path` | R6 |
| `test_load_catalog_rejects_key_without_alnum` | TOML de `tmp_path` | R7 |
| `test_load_catalog_rejects_missing_file_and_bad_toml` (fichero inexistente, TOML roto, tabla de slug repetida) | rutas inválidas | R8 |
| `test_load_catalog_rejects_entry_without_name` | TOML de `tmp_path` | R9 |
| `test_catalog_loads_bundled` | ruta por defecto | R2 |
| `test_catalog_integrity` (claves únicas, sin alias redundantes, slugs únicos) | catálogo real | R5, R6 |
| `test_catalog_poll_labels` (15 etiquetas → slugs; nombres de `salf`/`alianca-cat`) | catálogo real | R10, R11 |
| `test_catalog_covers_2023_brands` | `brands_2023.txt` (≥50 líneas; cada una resuelve) | R12, R28 |
| `test_catalog_punctuation_pairs` (10 pares → misma ficha) | catálogo real | R13 |
| `test_catalog_families_resolve` (lista de familias) | catálogo real | R14 |
| `test_catalog_coalitions_do_not_merge` (`podemos`/`unidas-podemos`/`sumar` → 3 slugs) | catálogo real | R15 |
| `test_resolve_uses_catalog_slug` (ficha → fila por slug o creación con `name` de la ficha) | resolver + TOML `tmp` | R17 |
| `test_resolve_catalog_creation_without_warning` | `caplog` | R18 |
| `test_resolve_matches_existing_name` (no crea fila) | resolver + `tmp` | R19 |
| `test_resolve_tie_break_slug_wins` | dos filas homónimas | R20 |
| `test_resolve_tie_break_lowest_id` | dos filas homónimas sin slug canónico | R21 |
| `test_resolve_creates_with_warning` (`name` literal, slug recortado, warning) | resolver + `tmp` + `caplog` | R22, R24 |
| `test_resolve_collision_suffix` (con `code` → `-code`; sin → `-2`) | resolver + `tmp` | R23 |
| `test_resolve_is_idempotent` (dos llamadas → una fila, un warning) | resolver + `tmp` + `caplog` | R25 |
| `test_resolve_no_fuzzy_matching` (`PPX` no resuelve a `pp`) | resolver + `tmp` | R16 |
| `test_slugify_single_source` (`election.slugify is parties.slugify is polls.slugify` + casos) | módulos | R26 |
| `test_module_has_no_new_dependencies` (imports por `ast` ⊆ stdlib + `ingestor`; `pyproject.toml` con las cuatro dependencias aprobadas) | fuente + `pyproject.toml` | R27 |

La fixture `brands_2023.txt` se genera con el volcado de §Curación (una grafía por línea, literal); su presencia y el umbral de líneas evitan que el test pase con una fixture vacía.

## Documentación

Esta feature no cambia cómo funciona nada (el módulo aún no lo usa ningún loader), así que los documentos de comportamiento (`docs/ingestor/ingesta.md`, `ingestor/AGENTS.md`, `.agents/data-model.md`) se actualizan en la feature 13, que es la que integra el resolver y cuya `acceptance` ya lo exige («docs al día»). No se adelanta aquí para no documentar como vigente un camino que aún no corre.

## Alternativas descartadas

1. **Catálogo en tabla de BD** (mudanza del fichero a `silver`): la curación es de repo y el diff es el registro de las decisiones; una tabla entra cuando la curación deje de ser de repo (UI), y entonces se muda. Hoy no hace falta.
2. **Fuzzy-matching** (`difflib`, similitud): una fusión equivocada entre marcas distintas distorsiona en silencio y no deja diff; el criterio es normalización exacta o alias explícito.
3. **Mapeo en código** (extender `PARTY_COLUMNS` a un dict compartido): curar identidad obligaría a tocar código y cada curación sería un cambio de programa; el TOML es dato revisable sin lógica.
4. **Catálogo exhaustivo de las 547 filas**: innecesario; los micro-partidos de un solo proceso resuelven por coincidencia de nombre (R19) y las fichas del alcance cubren el resto.
5. **Resolver con `Session`** (consultar la BD por etiqueta, API tipo `resolve_party(session, label)`): acopla la lógica a SQLAlchemy y obliga a base de datos en los tests; el índice en memoria sobre las filas existentes (una lectura de 547 filas por proceso de ingesta) es igual de simple y testeable en puro.
6. **Guardar alias redundantes** (grafías que ya coinciden por normalización): ruido y una segunda fuente de verdad para lo mismo; la carga los rechaza (R6).
7. **Comparar claves normalizadas fuera del catálogo** (normalizar en cada llamador): repetiría el fallo que la feature corrige; normalizar es del módulo.

## Interfaz para las features 13 y 14

```python
from ingestor.parties import load_catalog, PartyResolver

catalog = load_catalog()
resolver = PartyResolver(session.scalars(select(Party)), catalog)
party = resolver.resolve(head.short_name or head.name, code=head_code)  # elecciones
session.add(party)   # no-op si ya era persistente; flush después
```

- Elecciones (feature 13): sustituye el cuerpo de `_resolve_parties`; el `code` del sufijo es el código de la cabecera nacional (comportamiento de colisión actual).
- Sondeos (feature 14): el adaptador puede resolver rótulos de columna con `catalog.lookup(label)` (slug canónico) y el loader con el mismo `PartyResolver`; `PARTY_COLUMNS` se sustituye. `salf` y `alianca-cat` se crean desde su ficha (R17) cuando llegue su primera etiqueta.
- El pase de resolución de elección de los sondeos (`resolve_poll_elections`) no se ve afectado (los `party_id` no cambian de semántica).
