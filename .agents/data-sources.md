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

- Registros de longitud fija, uno por línea; delimitador CR+LF según la especificación.
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

El loader trabaja sobre una copia en `data/raw/congreso/{código}/` (solo los `.DAT`, sin ZIP) y lee 02/03/09/10; los 05–08 no se cargan y el 04 queda fuera (ver [plans/ingest-spec.md](plans/ingest-spec.md)).

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

Los nombres de CCAA, provincia y municipio salen del fichero oficial del INE («Relación de municipios y sus códigos»), que se descargará a `refs/ine/` y se cargará con `load-geography` (idempotente). Para municipios de una elección que ya no existan en el gazetteer actual, el loader usa el nombre del 05 de esa misma elección (ver [plans/ingest-spec.md](plans/ingest-spec.md)).

## Diferencias observadas entre procesos (¡ojo si sorprende algo!)

- **04 (1986 y 2000) solo lista a los elegidos** (350 filas, todas «S»); en el resto está la lista completa de candidatos más los 350 elegidos.
- **04 de 2023 usa CRLF** (único fichero de la serie; registro de 121 en vez de 120) y el DNI va en blanco. El resto: LF.
- **DNI (04, cols. 110–119)**: enmascarado de forma variable (ceros, espacios o primer carácter); nunca completo.
- **Flag «datos oficiales» (09, col. 101)**: hasta 2004 solo van con «S» las 72 filas del CERA (las mesas van con «N»); desde 2008 van todas con «S».
- **CERE (cols. 38–51 de 09)**: a ceros en generales (solo aplica a municipales/europeas).
- **Nombres geográficos**: 09/10 no traen nombres, solo códigos; 05/07 sí (en mayúsculas en procesos antiguos, capitalizados en los recientes). El mapeo completo código INE → nombre requiere un gazetteer, aún pendiente.
- **Municipios extintos**: códigos presentes en elecciones antiguas que ya no existen hoy (13 en 1986, 8 en 1989, 5 en 1996, 4 en 2004). No se descartan: se cargan con el nombre del 05 de su elección (ver [plans/ingest-spec.md](plans/ingest-spec.md)).

## Añadir otro proceso

1. Descargar `…/{tipo}{AAAA}{MM}_MESA.zip`.
2. Descomprimir en la carpeta del proceso (`refs/congreso/{código}/`; un ZIP = una carpeta).
3. Revisar `FICHEROS.doc` y las longitudes de registro por si el proceso introduce cambios (como los de arriba).
