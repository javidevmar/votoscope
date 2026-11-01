# Fuentes de datos

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Portal infoelectoral (Ministerio del Interior)

**Toda la información de los datos electorales de ámbito Congreso se encuentra en infoelectoral** (`https://infoelectoral.interior.gob.es`, portal del Ministerio del Interior): resultados, descargas y documentación de formato. Es la fuente primaria del proyecto; `refs/congreso/` y `data/raw/` son solo copias locales.

Los resultados oficiales se publican como ficheros de texto de **longitud fija** (`.DAT`) empaquetados en ZIP, por proceso electoral y **nivel de agregación**.

- URL de descarga: `https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/{tipo}{AAAA}{MM}_{NIVEL}.zip`
  - `{tipo}`: `02` = Congreso (`03` = Senado, `04` = municipales, `05` = autonómicas…).
  - Ejemplo: `02202307_MESA.zip` = Congreso, 23-jul-2023, nivel mesa.
  - La descarga es lenta e intermitente: usar curl con `--max-time` amplio, `--retry` y User-Agent de navegador (verificado 2026-10-12).
- Niveles (`NIVEL`): `MESA` ⊃ `MUNI` ⊃ `TOTA`.

| Nivel | Ficheros | Aporta |
| --- | --- | --- |
| `TOTA` | 01–04, 07, 08 | agregados por provincia / CCAA / total nacional |
| `MUNI` | 01–08 | + datos de ámbito municipal (05, 06) |
| `MESA` | 01–10 | + datos de mesa (09, 10) |

Comprobado en 2023-07: los ficheros presentes en más de un nivel son idénticos byte a byte, así que **el ZIP MESA es un superconjunto**; MUNI y TOTA solo sirven para descargar agregados sin el detalle de mesa. Para Votoscope basta MESA.

## Nomenclatura

- ZIP: `{tipo}{AAAA}{MM}_{NIVEL}.zip` (año a 4 dígitos).
- Dentro: `nnxxaamm.DAT` — `nn` = tipo de fichero (01–12), `xx` = tipo de proceso (`02` = Congreso), `aa` = año a 2 dígitos, `mm` = mes. Ejemplo: `09022307.DAT` = fichero 09, Congreso, 2023-07.

## Catálogo de ficheros

De `FICHEROS.doc` / `FICHEROS.rtf` (Ministerio del Interior), incluidos en cada ZIP:

| nn | Contenido |
| --- | --- |
| 01 | control: qué ficheros acompañan al proceso |
| 02 | identificación del proceso: fecha y horas (apertura, cierre, avances) |
| 03 | candidaturas: siglas, denominación y cabeceras de acumulación provincial/autonómica/nacional |
| 04 | candidatos |
| 05 | datos globales por municipio |
| 06 | votos por candidatura por municipio |
| 07 | datos globales de ámbito superior al municipio (provincia / CCAA / nación) |
| 08 | votos por candidatura de ámbito superior al municipio |
| 09 | datos globales por mesa y CERA |
| 10 | votos por candidatura por mesa y CERA |
| 11, 12 | municipios de menos de 250 habitantes (**solo elecciones municipales**) |

## Formato

- Registros de longitud fija, uno por línea; en la práctica el fin de línea es LF en toda la serie (la spec dice CR+LF; el único CRLF es el 04 de 2023).
- Codificación ANSI (**Windows-1252/ISO-8859-1**): hay caracteres acentuados; leer en latin-1, no en UTF-8.
- Campos numéricos alineados a la derecha y rellenos de ceros; alfanuméricos a la izquierda y rellenos de espacios.
- Layout campo a campo en `FICHEROS.doc` (idéntico en las 13 descargas de referencia; md5 `51bb96ff0466418dbf407fd8f695ad2f`).
- Longitudes de registro observadas en generales 1986–2023: 01=25, 02=40, 03=232, 04=120 (2023: 121 por CRLF, ver variaciones), 05=233, 06=33, 07=172, 08=33, 09=101, 10=36.

### 09 — datos por mesa (clave para el MVP)

`tipo2 · año4 · mes2 · vuelta1 · ccaa2 · provincia2 · municipio3 · distrito2 · sección4 · mesa1 · censo_INE7 · censo_escrutinio7 · censo_CERE7 · votantes_CERE7 · avance1_7 · avance2_7 · blancos7 · nulos7 · candidaturas7 · afirmativos7 (referéndum) · negativos7 (referéndum) · datos_oficiales1`

- No hay campo «votantes»: se deriva como `candidaturas + blancos + nulos`.
- Los avances de participación son parciales de la noche electoral; no el dato final.
- Filas CERA (voto exterior agregado): municipio `999`, distrito `09`, sección `0000`, mesa `U`; una por provincia, por CCAA y por total nacional (72 por proceso).

### 10 — votos por candidatura y mesa

Los 10 primeros campos iguales que 09, más `candidatura6 · votos7`.

## Copia local: `refs/congreso/`

Generales al Congreso **1986 → 2023** (13 procesos), nivel MESA, descomprimidas en `refs/congreso/{código}/` (ZIP original + los `.DAT` + `FICHEROS.doc`/`.rtf`). No se versiona (`.gitignore`): es material de referencia local para desarrollo y para el loader; el bronce del pipeline vivirá en `data/raw/` (ver [architecture.md](architecture.md)).

El loader trabaja sobre una copia en `data/raw/congreso/{código}/` (los `.DAT`, sin ZIP) y lee 02/03/09/10; el 05 solo se usa para nombrar municipios extintos, y 06–08 y el 04 quedan fuera (ver [`../ingestor/AGENTS.md`](../ingestor/AGENTS.md)).

| código | fecha | candidaturas (03) | filas 09 | filas 10 |
| --- | --- | --- | --- | --- |
| 02198606 | 22-06-1986 | 62 | 42.811 | 638.712 |
| 02198910 | 29-10-1989 | 100 | 44.354 | 794.464 |
| 02199306 | 06-06-1993 | 149 | 46.781 | 805.261 |
| 02199603 | 03-03-1996 | 112 | 49.289 | 607.954 |
| 02200003 | 12-03-2000 | 150 | 53.716 | 937.012 |
| 02200403 | 14-03-2004 | 137 | 56.657 | 1.088.214 |
| 02200803 | 09-03-2008 | 230 | 59.418 | 1.459.098 |
| 02201111 | 20-11-2011 | 127 | 59.948 | 758.440 |
| 02201512 | 20-12-2015 | 673 | 57.583 | 724.622 |
| 02201606 | 26-06-2016 | 81 | 57.603 | 634.585 |
| 02201904 | 28-04-2019 | 95 | 60.110 | 712.171 |
| 02201911 | 10-11-2019 | 106 | 59.627 | 770.595 |
| 02202307 | 23-07-2023 | 84 | 60.386 | 647.309 |

Las filas de 09 incluyen las 72 del CERA agregado: mesas = filas 09 − 72.

## Gazetteer INE

Los nombres de CCAA, provincia y municipio salen del fichero oficial del INE («Relación de municipios y sus códigos»), descargado a `refs/ine/` y cargado con `load-geography` (idempotente). Para municipios de una elección que ya no existan en el gazetteer actual, el loader usa el nombre del 05 de esa misma elección (ver [`../ingestor/AGENTS.md`](../ingestor/AGENTS.md)).

`refs/ine/` contiene los originales en `raw/` y tres CSV UTF-8 listos para el loader (edición del INE a 1-1-2026, publicada 2026-02-04):

| Fichero | Columnas | Filas |
| --- | --- | --- |
| `comunidades.csv` | `ine_code,name` (2 dígitos, 01–19) | 19 |
| `provincias.csv` | `ine_code,name,autonomous_community_ine_code` (2 dígitos, 01–52) | 52 |
| `municipios.csv` | `ine_code,name,province_ine_code` (5 dígitos) | 8.132 |

Fuentes (todas en `https://www.ine.es/daco/daco42/codmun/`, enlaces de la página de la operación, `cid=1254736177031`):

- `diccionario26.xlsx` («fichero completo», columnas `CODAUTO, CPRO, CMUN, DC, NOMBRE`) → `municipios.csv`; `26codmun.xlsx` (52 hojas) se usó para cotejar (0 discrepancias).
- `cod_ccaa.htm` → `comunidades.csv`; `cod_provincia.htm` y `cod_ccaa_provincia.htm` → `provincias.csv` (el mapeo provincia→CCAA se validó contra la columna `CODAUTO` del diccionario: 0 inconsistencias).
- Descarga con `curl` (User-Agent de navegador) y conversión puntual con `openpyxl` (sin tocar dependencias del proyecto).

Avisos del gazetteer: la CCAA 08 se llama `Castilla - La Mancha` (literal de `cod_ccaa.htm`; otras tablas del INE la escriben sin espacios); 184 municipios usan códigos de municipio 9xx (asignación real del INE para altas posteriores a la numeración alfabética, p. ej. `28903` Tres Cantos); el INE no publica en esta operación las entidades CERA (se crean al ingerir).

## Sondeos (Wikipedia)

`https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Spanish_general_election`
— página «Opinion polling for the 2026 Spanish general election»: encuestas de
intención de voto al Congreso desde las generales del 23-jul-2023. Alcance: la
sección *Voting intention estimates* (tablas por año, ámbito nacional).

- **Snapshot (bronce)**: wikitexto de una revisión fija
  (`data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext`), descargado por
  `uv run ingestor fetch-polls` (API, `oldid`) y cargado por
  `uv run ingestor ingest-polls` en `pollster`/`poll`/`poll_result`
  (`bronze.ingestion`, fuente `wikipedia-en`).
- **Formato**: tablas de wikitexto; `cabecera` a dos filas; cuatro columnas
  fijas (firma, fechas, muestra, `participación`) + columnas de partido +
  `Lead`; las celdas de partido llevan `%` y proyección de escaños.
- **Rarezas estructurales**:
  - `rowspan` en celdas de datos: los bloques del `CIS` y sus reestimaciones
    (`CIS {{smaller|(Target Point)}}`, `(Ateneo del Dato)`, `(Sondaxe)`,
    `(Demócrata)`, `(Logoslab)`) comparten fecha y muestra y se cargan como
    filas propias con el literal completo en `poll.source`. El valor de la
    celda se arrastra a las filas siguientes que cubre el `rowspan`.
  - Las tablas por año pueden partirse en varias tablas del mismo año: hoy
    `2026 (after FA)` (solo cabeceras) y `2026 (before FA)`.
  - Filas `separador` (una celda con `colspan`) y filas de `resultado` de una
    elección (`style="background:#EFEFEF"`, p. ej. generales 2023 y europeas
    2024): se saltan; los resultados ya viven en `vote`. La columna `Lead` se
    ignora (es derivable); las notas al pie (`{{efn|…}}`) y referencias
    (`<ref>…</ref>`) se descartan.
- **Papeles del literal de firma**: la columna «Polling firm/Commissioner» mezcla
  papeles y el loader los separa. `Encuestadora/Medio` (`SocioMétrica/El Español`):
  la encuestadora va a `pollster` y el medio/comisionante a `poll.media`.
  `CIS {{smaller|(Reestimador)}}` (`CIS (Target Point)`, `(Sondaxe)`, `(Logoslab)`…):
  el paréntesis del CIS es una proyección alternativa sobre sus datos brutos y su
  contenido va a `poll.reestimator`. Un literal sin separadores (`More in Common`,
  `CIS`, `PSOE`) solo tiene encuestadora: no se le inventan medio ni reestimador.
  El literal completo se conserva en `poll.source`; `CIS (JM)` y `CIS (Jaime Miquel)`
  se guardan tal cual, sin fusionar.
- **Rarezas de los valores**:
  - Fechas: un día (`5 Oct`), rango en el mismo mes (`10–11 Oct`) o entre
    meses (`29 Sep–1 Oct`); el año sale de la sección y un rango con `cruce de año`
    (`29 Dec–5 Jan`) resta uno al inicio. Cuando la página no conoce el trabajo
    de campo usa la `fecha de publicación` como aproximación: se guarda igual.
  - Porcentajes: `?` y `–` → nulo; `<2.0` (sin porcentaje) → nulo.
  - `participación` no numérica (p. ej. `66–67`) → `turnout` nulo con warning.
  - Celdas que son solo una nota (o un desglose) → sin valor en `poll_result`.
- **Licencia**: el texto de Wikipedia es **CC BY-SA**; al reutilizarlo hay que
  citar la fuente y enlazar la revisión usada
  (`https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid=1380859635`).
- **Verificación**: informe de ejecución, conteo de completitud y cotejo en
  [`../docs/ingestor/polls-run.md`](../docs/ingestor/polls-run.md).

## Diferencias observadas entre procesos (¡ojo si sorprende algo!)

Revisión proceso a proceso de las 13 generales (2026-10-12); lo que sigue es lo que el loader tiene en cuenta:

- **04 (1986 y 2000) solo lista a los elegidos** (350 filas, todas «S»); en el resto está la lista completa de candidatos más los 350 elegidos. **04 de 2023 usa CRLF** (único fichero de la serie; registro de 121 en vez de 120) y el DNI va en blanco.
- **DNI (04, cols. 110–119)**: enmascarado de forma variable (ceros, espacios o primer carácter); nunca completo.
- **Orden del 10**: no está ordenado por mesa (sobre todo 1986–2000): el loader agrupa por clave, nunca por orden.
- **Flag «datos oficiales» (09, col. 101)**: hasta 2004 solo van con «S» las 72 filas del CERA (las mesas van con «N»); desde 2008 van todas con «S». No se usa para filtrar.
- **CERE (cols. 38–51 de 09)**: a ceros en generales (solo aplica a municipales/europeas).
- **CERA**: 72 filas en 09 (52 provinciales + 19 CCAA + 1 nacional); las de provincia `99` son sumas del nivel provincial y triplican el CERA si se suman todas: el loader solo ingiere las 52 provinciales. El censo CERA va en el campo censo (en 1986, en censo de escrutinio); no es 0. 05 y 06 no traen fila 999.
- **Municipios extintos**: 13 códigos de 1986 que ya no están en el gazetteer INE actual (VILLOROBE, OZA DE LOS RIOS, CERDEDO, DARRICAL, EL ROBLEDO, ALCORLO, TORRECILLA DEL DUCADO, FRESNEDO, PEDROSA DEL REY, PALMEROLA, CESURAS, COTOBADE, GATOVA); el loader los crea con el nombre del 05 de su elección. En el resto de procesos no aparece ninguno nuevo.
- **Códigos de municipio ≥ 901**: son municipios reales (p. ej. El Ejido `04902`, Las Tres Villas `04901`); solo `999` es CERA.
- **Sección (09/10, cols. 19–22)**: hasta 1993, 4 dígitos; desde 1996, 3 dígitos + espacio o letra (A/B/C); CERA `0000`. Silver la guarda sin ceros a la izquierda («1», «11C») para que una sección sea una fila entre elecciones. La mesa es una letra (A–U); `U` es mesa única, no CERA.
- **05**: en Barcelona, Madrid, Málaga, Sevilla, Valencia y Zaragoza hay filas de distrito además del total municipal (`distrito=99`, el que usa el loader para los nombres). Los 05 son de edición posterior a su elección (el de 1986, de 2011).
- **Validación 09 ↔ 10 (votos por mesa)**: cuadra en 2004 y 2008–2023 (salvo 2015). No cuadra en 1986 (7 mesas, −563 votos), 1989 (15, −1.605), 1993 (16, −1.179), 1996 (16, −1.013) y 2000 (8, −461): el 10 pierde las primeras candidaturas en la primera mesa del primer municipio de algunas provincias (el 06 y el 09 las corroboran). En 2015 es al revés: 26.356 mesas con diferencias (neto −43.291) y el campo «candidaturas» del 09 es el inconsistente (06/07/08 cuadran con el 10). El adaptador degrada esta validación a warning en esos años.
- **2015, códigos CERA del 10**: las mesas CERA provinciales publican la candidatura como `9xxxxx`; el código real del 03 es `0xxxxx` (mapeo 9→0, verificado 605/605). En mesas normales no hay códigos `9xxxxx`.
- **2015, 03**: 673 filas = 605 candidaturas provinciales + 68 «cabeceras» `9xxxxx` (PP `903316`, PSOE `903484`…); el loader agrupa por cabecera nacional (56 partidos) y el resto de años lista cada partido una sola vez.
- **07/08 frente a 09/10**: el ministerio publica dos recuentos que no cuadran entre sí en varios procesos (1986, −9.642; 1989, −14.871; 1996, +979 en CERA; 2004, +3.788; 2008, +3 en Murcia; 2023, +175 en Toledo); en 2015 el 07/08 corrobora al 10. El MVP carga 09/10 y no usa 07/08; además el 08 acumula por cabecera, no por suma directa de códigos.
- **Nombres geográficos**: 09/10 no traen nombres, solo códigos; 05/07 sí (en mayúsculas en procesos antiguos, capitalizados en los recientes). El mapeo actual sale del gazetteer INE y el histórico del 05 de cada elección.
- **Mesas sin votos**: hay mesas con censo y avances pero sin votos (p. ej. 2 en 2004, 8 en 2019-04, 3 en 2023); se cargan tal cual, con votos a cero.

## Añadir otro proceso

1. Descargar `…/{tipo}{AAAA}{MM}_MESA.zip`.
2. Descomprimir en la carpeta del proceso (`refs/congreso/{código}/`; un ZIP = una carpeta).
3. Revisar `FICHEROS.doc` y las longitudes de registro por si el proceso introduce cambios (como los de arriba).
