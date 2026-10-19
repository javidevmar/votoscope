# El ingestador: comandos y carga en `silver`

Cómo funciona `ingestor/`: los comandos, el comportamiento de la ingesta y qué acaba en el esquema `silver`.
Para el formato de los ficheros fuente y sus rarezas, ver [`../../.agents/data-sources.md`](../../.agents/data-sources.md); para el modelo de datos, [`../../.agents/data-model.md`](../../.agents/data-model.md).

## Comandos

Script de consola `ingestor`, ejecutado con `uv run ingestor …` desde `ingestor/`.

### `ingestor load-geography`

Carga el gazetteer INE en `silver` (`autonomous_community`, `province` y `municipality`).

- Lee `INE_DIR` (por defecto `refs/ine/`): `comunidades.csv`, `provincias.csv` y `municipios.csv` (formato y procedencia en [data-sources.md](../../.agents/data-sources.md)).
- Es idempotente: inserta lo que falta y actualiza nombres y mapeos; **no borra nada** (los pseudo-municipios CERA y los municipios extintos que crea la ingesta se conservan).
- Hay que ejecutarlo antes de la primera ingesta: `ingest` falla si falta una provincia.

```sh
uv run ingestor load-geography
```

### `ingestor ingest <ruta> [--force]`

Ingiere una elección, o varias, desde ficheros locales.

- `<ruta>` puede ser una carpeta de elección (con los `.DAT` dentro) o una raíz con varias carpetas de elección; se recorren todas en orden alfabético.
- El adaptador se elige por el código de proceso del fichero `02*.DAT` (Congreso = `02`; el registro está en `elections/adapters/`).
- Ficheros requeridos: `02`, `03`, `09` y `10`; el `05` es opcional (solo se usa para nombrar municipios extintos).
- Los ficheros deben estar bajo `RAW_DIR` (por defecto `data/raw/`), porque `bronze.ingestion.file_path` es relativo a esa carpeta. La copia de trabajo es `data/raw/congreso/{código}/`.
- Si todos los ficheros de una elección ya están `processed` en bronce (mismo sha256), la elección **se salta**; con `--force` se recarga igualmente.
- Un error en una elección no aborta las demás: se registra y se sigue; el proceso sale con código 1 si alguna falló (0 si todo quedó `processed` o `skipped`).

```sh
uv run ingestor ingest ../data/raw/congreso/02202307        # una elección
uv run ingestor ingest ../data/raw/congreso                 # todas las que haya
uv run ingestor ingest ../data/raw/congreso/02202307 --force
```

### `ingestor fetch-polls [--page <título>]`

Descarga a bronce el wikitexto de una revisión **fija** de la página de sondeos de Wikipedia (por defecto, «Opinion polling for the 2026 Spanish general election»).

- Resuelve la revisión actual con la API (`action=query&prop=revisions&rvprop=ids|timestamp&redirects=1`) y descarga el wikitexto de esa revisión con `index.php?oldid={revid}&action=raw` (la revisión queda fijada por `oldid`).
- Escribe en `RAW_DIR/polls/wikipedia-en/2026-general/{revid}.wikitext`; `--page` apunta a otra página y su carpeta pasa a ser un slug del título (p. ej. `opinion-polling-for-the-2027-spanish-general-election/`).
- Si esa revisión ya está en disco, no la repite: el ciclo **sin novedades es una sola llamada a la API** y termina con exit 0.
- Peticiones con `urllib` de la biblioteca estándar, User-Agent identificativo, timeout de 30 s y un reintento; si la petición falla tras el reintento, sale con exit 1 y log de error.
- No toca la base de datos: el registro en `bronze.ingestion` lo hará `ingest-polls` al cargar el snapshot.

```sh
uv run ingestor fetch-polls
uv run ingestor fetch-polls --page "Opinion polling for the 2027 Spanish general election"
```

### `ingestor ingest-polls [ruta] [--force]`

Carga en `silver` los sondeos de los snapshots de Wikipedia (ficheros `.wikitext`).

- `<ruta>` puede ser un fichero de snapshot o un directorio; sin ruta se procesan los `.wikitext` bajo `RAW_DIR/polls/` (recursivo). El nombre debe ser `{revision_id}.wikitext` y el fichero debe estar bajo `RAW_DIR` (bronce guarda rutas relativas).
- Registra cada snapshot en `bronze.ingestion` con su sha256, tamaño y `source = wikipedia-en`; si ya está `processed` (mismo sha256), se salta.
- **Guard de revisión**: un snapshot con `revision_id` anterior al máximo ya cargado (`max(poll.revision_id)`) se ignora con warning y no se registra en bronce; `--force` reprocesa tanto los `processed` como los anteriores.
- Antes de decidir qué snapshots están pendientes corre el **pase de resolución de elección** (ver «Comportamiento de `ingest-polls`»); también cuando no hay ningún snapshot nuevo.
- Un error en un snapshot no aborta los demás: se registra y se sigue; sale con código 1 si alguno falla (0 si todo queda `processed`/`skipped`, también sin snapshots pendientes).

```sh
uv run ingestor ingest-polls                                   # todo RAW_DIR/polls/
uv run ingestor ingest-polls ../data/raw/polls/wikipedia-en/2026-general/1380713440.wikitext
uv run ingestor ingest-polls ../data/raw/polls --force
```

## Configuración (entorno)

Variables de entorno (pydantic-settings; un `.env` en `ingestor/` las sobrescribe):

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `DATABASE_URL` | Postgres de `docker-compose.yml` (`localhost:5434`) | conexión a la base de datos |
| `RAW_DIR` | `data/raw/` (raíz del repo) | bronce: ficheros fuente inmutables |
| `INE_DIR` | `refs/ine/` | gazetteer INE en CSV |
| `LOG_LEVEL` | `INFO` | nivel de log (`DEBUG`…`CRITICAL`) |

## Comportamiento de `ingest`

Por cada carpeta de elección, todo el trabajo de plata va en **una transacción**; el registro en bronce y los cambios de estado van en transacciones aparte:

1. **Identificación**: se localizan los ficheros, se comprueba que están bajo `RAW_DIR` y se parsea el `02` (tipo de proceso y fecha de celebración).
2. **Bronce**: se calcula el sha256 de cada fichero. Los sha nuevos se registran en `bronze.ingestion` (`registered`, ruta relativa, tamaño, fuente `infoelectoral`). Si todos los ficheros de la elección ya están `processed`, se salta (salvo `--force`).
3. **Recarga**: se busca o crea la fila de `silver.election` y se **borran** los hechos y candidaturas previos de esa elección (`vote`, `turnout` y `party_election`). Reingerir una elección = borrar y recargar; `party` (identidad) y la geografía no se tocan.
4. **Candidaturas** (`03`): cada **cabecera nacional** se resuelve con la resolución
   compartida de `parties.py` sobre el catálogo `data/party_catalog.toml` (catálogo →
   nombre existente → alta con warning): las grafías de la misma marca (`B.N.G.`/`BNG`)
   acaban en una sola fila de `party`, con el slug canónico del catálogo (si el slug
   choca, lleva el código de cabecera). Cada fila del `03` se inserta como
   `party_election`, con su código, siglas y denominación.
5. **Mesas y participación** (`09`): se descartan las filas agregadas de CERA (provincia `99`) y, por cada mesa:
   - el municipio se resuelve contra la geografía; si no existe, se crea: pseudo-municipio CERA (`<provincia>999`, nombre «CERA») o municipio extinto con el nombre del `05` de esa misma elección (si no hay nombre en ninguna fuente, queda `NULL` y se avisa por log);
   - la mesa (`polling_station`) se busca o crea por (municipio, distrito, sección, código): es agnóstica a la elección;
   - se inserta el `turnout` (censo INE, blancos y nulos).
6. **Votos** (`10`): se descartan los agregados de CERA, se normalizan los códigos `9xxxxx` de 2015, se comprueba que cada candidatura existe en el `03` y cada mesa en el `09` (si no, error y rollback) y se insertan los `vote` por candidatura y mesa. Las filas con 0 votos no se guardan.
7. **Validación**: la suma de votos del `10` debe cuadrar con el campo «votos a candidaturas» del `09` de cada mesa. En los procesos donde los ficheros del ministerio no cuadran entre sí (1986, 1989, 1993, 1996, 2000, 2004 y 2015; ver [data-sources.md](../../.agents/data-sources.md)) se degrada a warning; en el resto, una diferencia aborta la elección.
8. **Estados**: si todo va bien, el commit deja los hechos en `silver` y los ficheros pasan a `processed`; si algo falla, la transacción se deshace y los ficheros de esa ejecución quedan `failed` (la próxima ejecución la reintenta).

## Comportamiento de `ingest-polls`

Por cada snapshot, todo el trabajo de plata va en **una transacción**; el registro en bronce y los cambios de estado van en transacciones aparte (igual que en `ingest`):

1. **Resolución de elección**: al inicio de cada ejecución, cada sondeo con `election_id` nulo se enlaza a la primera elección del mismo `election_type`, de ámbito nacional (sin CCAA ni municipio) y fecha estrictamente posterior a su `fieldwork_end`. Sin candidata o sin `fieldwork_end`, queda nulo. Es idempotente (solo mira los nulos), así que un sondeo cargado en una ejecución queda enlazado en la siguiente.
2. **Bronce**: se calcula el sha256 del snapshot. Si no está en `bronze.ingestion`, se registra (`registered`, ruta relativa a `RAW_DIR`, tamaño, fuente `wikipedia-en`); si ya está `processed`, se salta (salvo `--force`).
3. **Guard de revisión**: si el `revision_id` es anterior a `max(poll.revision_id)`, el snapshot se ignora con warning y sin registrar (salvo `--force`).
4. **Parseo**: el wikitexto se convierte en filas de sondeo con el adaptador de la fuente (`polls/adapters/wikipedia_polls.py`).
5. **Validaciones** (antes de tocar `silver`): cada fila necesita firma (literal y nombre de encuestadora) y al menos dos partidos con valor; porcentajes 0–100, escaños 0–350 y `seats_min ≤ seats_max`; un snapshot sin sondeos es error (protege el borrado total de `silver`). La suma de porcentajes de un sondeo por encima de 100.5 solo avisa (la página no publica «otros»).
6. **Plata (una transacción)**: get-or-create de `pollster` (por el slug de la firma) y de `party` (slugs del mapeo; un rótulo desconocido de una columna nueva se da de alta con su slug y un warning), **borrado total** de `poll`/`poll_result` e inserción de las filas del snapshot. `silver` refleja el último snapshot ingerido; el histórico de revisiones vive en bronce.
7. **Estados**: si todo va bien, los sondeos quedan en `silver` y el fichero pasa a `processed`; si algo falla, la transacción se deshace y el fichero queda `failed` (la próxima ejecución lo reintenta).

## Qué queda en `silver`

| Tabla | Contenido |
| --- | --- |
| `autonomous_community`, `province`, `municipality` | geografía INE; los municipios CERA y los extintos los crea la ingesta; `name` solo es `NULL` si no hay nombre en ninguna fuente |
| `election` | una fila por proceso (tipo `congress`, fecha; ámbito nulo = nacional) |
| `party` | identidad del partido (catálogo `data/party_catalog.toml` vía `parties.py`; `slug` único) |
| `party_election` | candidatura por elección, tal y como la publica el `03` |
| `polling_station` | mesa (municipio, distrito, sección, código), compartida entre elecciones |
| `turnout` | censo INE, blancos y nulos por mesa y elección |
| `vote` | votos por candidatura y mesa (las filas con 0 votos no se guardan) |
| `pollster` | encuestadora que firma el sondeo (slug único; se crea al vuelo desde la firma) |
| `poll` | un sondeo por fila del snapshot: `source` (literal de cabecera), `election_type` (`congress`), `election_id` (nulo hasta que el pase de resolución encuentra elección), fechas de trabajo de campo, muestra, participación y `revision_id` de procedencia |
| `poll_result` | porcentaje y proyección de escaños (`seats_min`/`seats_max`) por partido y sondeo |

- Los votantes no se almacenan: se derivan como `sum(vote.votes) + blank_votes + null_votes`.
- Los sondeos (`pollster`, `poll`, `poll_result`) los carga `ingest-polls` y se reemplazan enteros en cada carga: `silver` refleja el último snapshot ingerido, no un histórico.
- No se cargan: el `04` (candidatos), los agregados `05`–`08` (el `05` solo se usa como fuente de nombres) ni las filas agregadas de CERA (CCAA y nacional: son sumas de las provinciales).
- `bronze.ingestion` guarda una fila por fichero leído (ruta, sha256, tamaño, fuente y estado).
