# Ejecución real y cotejo de los sondeos

- Feature 11 (`polls_run`), rama `feature/polls-run`, fecha 2026-10-18.
- Página: «Opinion polling for the 2026 Spanish general election» — revisión
  [1380859635](https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid=1380859635).
- Snapshot: `data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext`
  (651.942 bytes; sha256 `8a21b27fd3ec6c05bd2766ef3ef98a8f2f3780378b43b0a83d066b43b18f50c2`).

## Comandos ejecutados

```sh
cd ingestor
uv run ingestor fetch-polls     # exit 0 — revid=1380859635, snapshot descargado
uv run ingestor ingest-polls    # exit 0 — revision 1380859635 processed (575 polls)
```

Salida relevante de `fetch-polls`:

```text
INFO ingestor.polls.fetch resolved page=Opinion polling for the 2026 Spanish general election revid=1380859635 timestamp=2026-10-18T11:36:42Z
INFO ingestor.polls.fetch downloaded snapshot .../data/raw/polls/wikipedia-en/2026-general/1380859635.wikitext
```

Salida relevante de `ingest-polls` (los dos snapshots anteriores ya estaban
`processed` y se saltaron; los avisos son del snapshot nuevo):

```text
INFO ingestor.polls.loaders.polls .../1380713440.wikitext: skipped (already processed)
INFO ingestor.polls.loaders.polls .../1380777984.wikitext: skipped (already processed)
WARNING ingestor.polls.adapters.wikipedia_polls unknown party column: FA
WARNING ingestor.polls.adapters.wikipedia_polls unknown party column: FV
WARNING ingestor.polls.adapters.wikipedia_polls unparseable turnout: 66–67
INFO ingestor.polls.loaders.polls .../1380859635.wikitext: processed revision 1380859635 (575 polls)
```

## Completitud

Método: declaradas = filas `|-` de cada tabla por año (incluye las dos filas de
cabecera); cargadas = `silver.poll` con `revision_id = 1380859635`. Las filas
saltadas se clasifican por diseño: cabeceras (`!`), separadoras (una celda con
`colspan`) y filas de resultado de una elección (`style="background:#EFEFEF"`).

| Tabla (año) | Declaradas | Cargadas | Saltadas |
| --- | --- | --- | --- |
| 2026 (after FA) | 2 | 0 | 2 cabeceras |
| 2026 (before FA) | 160 | 158 | 2 cabeceras |
| 2025 | 180 | 178 | 2 cabeceras |
| 2024 | 171 | 168 | 2 cabeceras + 1 resultado (europeas 2024) |
| 2023 | 76 | 71 | 2 cabeceras + 2 separadoras + 1 resultado (generales 2023) |
| **Total** | **589** | **575** | **14** |

Aritmética: declaradas (589) = cargadas (575) + saltadas (14). En `silver` hay
575 `poll` (todos con `revision_id = 1380859635`), 6.125 `poll_result` y 28
`pollster`; `pollster` y `party` no se borran entre snapshots, solo se
reemplazan `poll` y `poll_result`.

Frente a la referencia ≈584 del plan (157 + 180 + 171 + 76): +5 filas
declaradas. La diferencia está en 2026: la página partió la anualidad en
`2026 (after FA)` (2 filas, solo cabeceras) y `2026 (before FA)` (160 filas),
162 en total frente a las 157 de la referencia; las otras tres anualidades
siguen en 180/171/76. Ninguna fila declarada queda sin explicación.

## Método (reproducible)

```sql
-- cargadas del snapshot (575)
select count(*) from silver.poll where revision_id = 1380859635;
-- resultados (6.125) y encuestadoras (28)
select count(*) from silver.poll_result;
select count(*) from silver.pollster;
-- snapshots de la fuente en bronce (3 processed: 2 previos + el de esta ejecución)
select count(*) from bronze.ingestion where source = 'wikipedia-en' and status = 'processed';
-- desglose por anualidad del trabajo de campo (71/168/178/158)
select extract(year from fieldwork_end), count(*) from silver.poll group by 1 order by 1;
```

`revision_id` de procedencia: 1380859635. Enlace a la revisión usada:
`https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid=1380859635`.

## Fuera de alcance

- Columna `Lead` (derivable de los porcentajes; el adaptador la ignora).
- Tablas de secciones distintas de *Voting intention estimates* (*Voting
  preferences*, *Victory likelihood*, *Hypothetical scenarios* y subnacionales).
- Columnas de partido sin filas de datos en las tablas del alcance: `FA`
  (*Broad Front*) y `FV` (*Valencian Front*); solo aparecen en la cabecera de
  `2026 (after FA)`, que no tiene filas de datos. No generan `poll_result`.

## Avisos observados

- `unknown party column: FA` — columna de partido desconocida en la cabecera de
  `2026 (after FA)`; se conserva el rótulo crudo y no hay filas de datos que
  cargar. Efecto: ningún `poll_result` de `FA` en esta revisión.
- `unknown party column: FV` — columna nueva en la misma cabecera (no estaba en
  la revisión anterior); mismo tratamiento y mismo efecto nulo.
- `unparseable turnout: 66–67` — la participación de
  `Ipsos/La Vanguardia` (15–21 May 2025, muestra 2.000) no es numérica; se carga
  como `turnout` nulo (warning del adaptador, la fila se conserva).

## Cotejo

Muestra de 6 sondeos contra el wikitexto de la revisión (firma, fechas, % y
escaños); cada fila compara página → `silver` (el porcentaje se guarda con dos
decimales). Comprobados también muestra y participación cuando la página los
publica.

| Firma (source) | Fechas | Comprobación (página → silver) | Veredicto |
| --- | --- | --- | --- |
| SocioMétrica/El Español | 10–11 Oct 2026 | PP 32,6 % / 141 escaños → 32,60 / 141; PSOE 26,2 % / 104 → 26,20 / 104 | OK |
| Sigma Dos/El Mundo | 22–29 Dec 2025 | PP 32,7 % / 141 escaños → 32,70 / 141; PSOE 26,5 % / 107 → 26,50 / 107 | OK |
| SocioMétrica/El Español | 26–30 Dec 2024 | PP 33,5 % / 146 escaños → 33,50 / 146; PSOE 28,3 % / 116 → 28,30 / 116 | OK |
| SocioMétrica/El Español | 25–31 Dec 2023 | PP 38,7 % / 154 escaños → 38,70 / 154; PSOE 29,2 % / 115 → 29,20 / 115 | OK |
| EM-Analytics/Electomanía | 24–25 Jul 2023 | PP 31,8 % / 129 escaños → 31,80 / 129; PSOE 33,0 % / 127 → 33,00 / 127 | OK |
| Ipsos/La Vanguardia | 15–21 May 2025 | PP 34,4 % / 145 escaños → 34,40 / 145; PSOE 30,4 % / 128 → 30,40 / 128 | OK |

Nota: la celda de participación `66–67` de ese último sondeo degrada a nula
(warning del adaptador); el resto de valores de la fila se carga con normalidad.
La fila de 24–25 Jul 2023 es la más antigua del alcance y su trabajo de campo
arranca el 24-jul-2023, un día después de las generales.
