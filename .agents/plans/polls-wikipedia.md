# Sondeos desde Wikipedia (generales 2026)

Estado: abierto · Creado: 2026-10-12 · Abierto: 2026-10-12 · Actualizado: 2026-10-12, 2026-10-17
Objetivo: ingerir las encuestas de intención de voto al Congreso de la página «Opinion polling for the 2026 Spanish general election» (Wikipedia en inglés) como hechos en `silver`, desde snapshots de revisión fija en bronce, sincronizados **dos veces al día** para captar cada sondeo nuevo, y dejar fijado el contrato para las vistas `gold` de la web.
Rama: feature/polls

## Decisiones a confirmar al arrancar

1. **Descarga en el ingestador.** Un comando nuevo, `fetch-polls`, baja el snapshot de la página (revisión fija) a `data/raw/`. Esto matiza la regla «el ingestador no descarga nada» de [`architecture.md`](../architecture.md): los datos electorales siguen siendo manuales; los sondeos se bajan por CLI porque la revisión fija es parte del contrato, no un paso manual. Alternativa descartada: `curl` a mano (cada refresco dependería de que alguien recuerde la revisión exacta).
2. **Fuente única: Wikipedia en inglés** (la página que se verificó y usó para diseñar el parser). La española queda como contraste manual si algún dato chirría: mismo esqueleto, pero formato más sucio (estilos en línea), secciones extra («Intención de voto directa», «Por bloque ideológico») y menos filas.
3. **`silver` refleja el último snapshot ingerido** (reemplazo total de `poll`/`poll_result`), no un histórico de revisiones: el histórico queda en bronce. Ingerir un snapshot viejo retrocede `silver`; un guard por `revision_id` lo ignora salvo `--force`.
4. **Sin elección inventada.** Los sondeos apuntan a una elección que aún no ha ocurrido, así que `poll.election_id` es nullable (+ `election_type`). El enlace lo materializa un pase de resolución en `ingest-polls` (feature 9): cada sondeo con `election_id` nulo se enlaza a la primera elección del mismo tipo y ámbito posterior a su trabajo de campo; corre en cada ejecución, también sin snapshot nuevo, así que el día que se ingiera la elección de 2026 los pendientes quedan enlazados solos (≤12 h). El criterio es data-driven (`election_type` + ámbito + fecha): cuando lleguen los sondeos autonómicos (futuro, con su ámbito en `poll`) la misma regla casa sin rediseño. No se crea una fila falsa en `silver.election` con fecha estimada.
5. **Alcance mínimo**: solo la sección *Voting intention estimates* (tablas 2023–2026, ámbito nacional, Congreso). Fuera: preferencias de voto, probabilidad de victoria, escenarios hipotéticos, sondeos por CCAA y liderazgos (futuro, por ese orden de interés).
6. **Job programado 2×/día** (requisito fijado): ver «Ejecución periódica». Queda por cerrar solo el mecanismo (cron/launchd local hoy; `schedule:` de GitHub Actions contra el entorno de destino cuando exista).

## La fuente

`https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Spanish_general_election`. Verificada el 2026-10-12 (revisión `1379921971`; ~646 KB de wikitexto). Es un agregador de agregadores: cada fila enlaza al sondeo original (CIS, medios, encuestadoras), y el rango temporal va de las generales de 2023 al presente.

- Cuatro tablas bajo *Voting intention estimates*, una por año (2026, 2025, 2024, 2023), en orden inverso; ≈584 filas declaradas (157/180/171/76), sin contar la expansión de `rowspan`.
- Cabecera en dos filas `!`: cuatro columnas fijas (`Polling firm/Commissioner`, `Fieldwork date`, `Sample size`, `Turnout`), columnas de partido y `Lead`. La primera fila identifica al partido con `[[File:…|link=Partido|PP]]` (rótulo = alt del fichero; si no lo hay, el destino del `link=`); la segunda solo lleva `{{party color|…}}` y se ignora.
- Las columnas de partido **no son fijas entre años**: 2023 no tiene SALF, Aliança.cat ni Adelante Andalucía; 2024 añade SALF; 2025, Aliança.cat; 2026, Adelante Andalucía (15 columnas). Siempre por cabecera, nunca por posición.
- Celdas de partido: `{{Party shading/PP}}| '''32.6'''<br/>{{font|size=75%|font=Verdana|text=141}}` = % (en negrita el que gana) + proyección de escaños en cuerpo menor; `?` = desconocido; `–` = no listado; escaños `135/137` = rango, `8` = valor único, `?` = desconocido. La última celda es `Lead` (se ignora: derivable).
- Rarezas que el parser debe tratar (verificadas en el wikitexto):
  - `rowspan="N"` en celdas de datos: los bloques del CIS y sus reestimaciones comparten fecha y muestra (y a veces la firma); hay que arrastrar el valor a las N−1 filas siguientes.
  - Reestimaciones alternativas del CIS: `CIS {{smaller|(Target Point)}}`, `(Ateneo del Dato)`, `(Sondaxe)`, `(Demócrata)`, `(Logoslab)`, con la nota «Alternative projection based on raw CIS data». Se cargan como filas propias; el literal completo queda en `poll.source`.
  - Notas al pie `{{efn|…}}` (p. ej. «Includes separate figures for Compromís») y referencias `<ref>…</ref>`: se descartan (quedan en bronce); una celda que es solo una nota vale nulo.
  - Filas separadoras `| colspan="17" style="background:#A0A0A0"|` y la fila final gris del resultado de las generales de 2023 (`style="background:#EFEFEF"`): se saltan; los resultados ya viven en `vote`.
  - Fechas: `10–11 Oct`, `5 Oct`, `29 Sep–1 Oct`, `?`; el año sale de la sección; los rangos que cruzan año (`29 Dec–5 Jan`) restan uno al inicio. Cuando la página no conoce el trabajo de campo usa la fecha de publicación: se guarda igual, la limitación es de la fuente.
  - Saltos de línea `<br/>` y `<br />`; un único `<2.0` (sin porcentaje).
  - Sin desglose de «otros»/indecisos por diseño: los % no suman 100.

## Obtención (bronce)

- `ingestor fetch-polls` (nuevo): resuelve la revisión actual de la página vía API (`action=query&prop=revisions&rvprop=ids|timestamp&redirects=1`) y descarga el wikitexto de esa revisión (`index.php?oldid={revid}&action=raw`) a `data/raw/polls/wikipedia-en/2026-general/{revid}.wikitext`. Si esa revisión ya está bajada (`{revid}.wikitext` existe), no la repite: el ciclo programado sin novedades es una sola llamada a la API. Con `urllib` de la biblioteca estándar (sin dependencias nuevas), User-Agent identificativo, timeout y un reintento.
- La revisión fija hace el snapshot determinista y reproducible; el bronce es inmutable como el resto (`bronze.ingestion` por sha256, `source = wikipedia-en`).
- `--page` permite apuntar a otra página (el día que se renombre a «2027…» o «next…», o para el contraste con la española); por defecto, la de 2026 como constante del adaptador.
- `ingestor ingest-polls [ruta]` (nuevo): parsea los snapshots pendientes de `data/raw/polls/` (o de la ruta dada) y carga `silver`; si todos están `processed`, se salta; `--force` recarga.

## Ejecución periódica (2×/día)

- La página se edita a diario (sondeos nuevos, correcciones), así que esto no es una carga de una sola vez: un job **cada 12 h** consulta la revisión actual y solo baja e ingiere si cambió. La web lee `silver`/`gold` al vuelo, así que cada sincronización se refleja sola, sin despliegues.
- Sin novedades el ciclo es una única llamada ligera a la API y termina con exit 0 sin escribir nada: `fetch-polls` no rebaja una revisión que ya está en `data/raw/` e `ingest-polls` se salta lo `processed`.
- Cualquier edición (aunque sea de formato) crea revisión nueva y provoca recarga completa de `poll`/`poll_result` con los mismos datos: ids sustitutos nuevos, inocuo. Si algún día molesta, se compara el resultado del parseo antes de recargar; ahora no hace falta.
- Mecanismo: **cron/launchd local** mientras el destino sea el Postgres de docker-compose (documentarlo en [`environment.md`](../environment.md)); cuando la Entrega fije la topología de entornos, el mismo job pasa a `schedule:` de GitHub Actions (y la alerta correspondiente). Pensado para correr sin nadie mirando: página ausente o renombrada → exit ≠ 0 y log para que se vea.

## Parser (wikitexto)

- Formato elegido: **wikitexto**, no HTML. Es la fuente canónica, más pequeño y sin ruido de render (referencias como superíndices, entidades). Verificado que las tablas de intención de voto usan una celda por línea (sin `||`) y solo tres formas de prefijo de celda: `| valor`, `rowspan="N"| valor` y `style="…"| valor` / `{{Party shading/X}}| valor`.
- Estructura: `parsers/wikitext.py` (lexer genérico: bloques `{|…|}`, filas `|-`, celdas `|`/`!`, expansión de `rowspan`, limpieza de `{{efn}}`, `<ref>`, `'''`, `{{smaller|X}}`→X, `{{font|…|text=X}}`→X, `<br>`) + `adapters/wikipedia_polls.py` (reglas de esta fuente: secciones y tablas por año, cabecera, filas → `Poll`/`PollResult`, fechas, números, mapeo de partidos, saltos).
- Mapeo de columnas → `silver.party` (slug existente; si falta, se crea con nombre legible): PP→`pp`, PSOE→`psoe`, Vox→`vox`, Sumar→`sumar`, ERC→`erc`, Junts→`jxcat-junts`, EH Bildu→`eh-bildu`, PNV→`eaj-pnv`, BNG→`bng`, CCa→`cca`, UPN→`u-p-n`, Adelante Andalucía→`adelante-andalucia`, Podemos→`podemos`. SALF→`salf` («Se Acabó La Fiesta») y Aliança.cat→`alianca-cat` («Aliança Catalana») no existen: se crean. Queda viva la deuda de curación de identidades de partido ya anotada en [`data-model.md`](../data-model.md); cuando se ingiera la elección de 2026 se revisará que el loader de elecciones no duplique estas.
- Columna de partido desconocida (la wiki añade una) → warning y se ignora la columna; los tests fijan las 15 conocidas.
- Tests con fixtures en `tests/fixtures/wikipedia_polls/`: recortes reales (cabecera + primeras filas de 2026, incluido el bloque del CIS con `rowspan`; cola de 2023 con separadores y fila de resultado) + casos sintéticos (cruce de año, `<br />`, `–` vs `?`, `<2.0`, rango de escaños, celda-nota). Sin red y sin `refs/`.

## Modelo (silver)

Tres tablas nuevas, con la regla de sincronización de siempre (ERD ↔ `models.py` ↔ migración):

- **`pollster`**: `id` PK, `name`, `slug` UK(60) — la casa que firma el sondeo (se extrae del literal: lo que va antes de «(» o «/»; p. ej. «SocioMétrica/El Español» → SocioMétrica). Patrón de `party`.
- **`poll`**: `id` PK; `pollster_id` FK; `source` (literal de la cabecera, p. ej. «SocioMétrica/El Español», para pintar); `election_type` ('congress', mismo vocabulario que `election.type`); `election_id` FK nullable; `fieldwork_start` / `fieldwork_end` DATE nullables; `sample_size` INT nullable; `turnout` NUMERIC(5,2) nullable (con CHECK 0–100); `revision_id` BIGINT (procedencia y guard de recarga).
- **`poll_result`**: `id` PK; `poll_id` FK indexada; `party_id` FK indexada; `pct` NUMERIC(5,2) nullable (`?`, `–` y `<2.0` → nulo; CHECK 0–100); `seats_min` / `seats_max` INT nullables (valor único → min = max); UK (`poll_id`, `party_id`).

```
pollster 1─n poll 1─n poll_result n─1 party
                 └──(nullable)── election
```

- No se guardan: `Lead` (derivable), notas al pie ni referencias (viven en el bronce), ni la fila del resultado de 2023 (vive en `vote`).
- ERD: **dos páginas nuevas** en `docs/db/schema.drawio` — *Bronze polls* y *Silver polls* — para no mezclar los sondeos con las páginas Bronze/Silver de las elecciones:
  - *Silver polls*: `pollster`, `poll` y `poll_result` completas; `party` y `election` como cajas de referencia atenuadas, solo para poder trazar las FK.
  - *Bronze polls*: el flujo del sondeo (snapshot `.wikitext` en `data/raw/polls/…` → `bronze.ingestion`), con `ingestion` como referencia a la página Bronze (tabla compartida).
  - Validar con la skill `database-erd-drawio`. En [`data-model.md`](../data-model.md), la frase «una página por esquema» pasa a «una página por esquema y dominio (Bronze, Silver, Bronze polls, Silver polls)». Migración autogenerada y `alembic check` sin drift.

## Carga (bronce → plata)

- `ingest-polls`: registra el fichero en `bronze.ingestion` (source `wikipedia-en`, sha256) → parsea → en una transacción, get-or-create de `pollster` y de los partidos que falten, borrado de `poll`/`poll_result` e inserción del snapshot → `processed`. Fallo → rollback y `failed`, como las elecciones.
- Guard de revisión: si el `revision_id` del snapshot es anterior al ya cargado (`max(poll.revision_id)`), se ignora con warning; `--force` lo reprocesa.
- Validaciones mínimas (rollback si fallan las estructurales): cada fila produce firma y ≥2 partidos con valor; porcentajes y escaños en rango; suma de % del sondeo ≤ 100.5 (warning, la página no publica «otros»). No se valida contra la página española.

## Gold y web (fuera de este plan)

- Contrato propuesto para la entrega: una vista de sondeos (poll + pollster + party + pct + escaños + fechas + `source`/`revision_id`) y una vista «orden por trabajo de campo» para el gráfico de tendencia y la tabla. Los colores de partido (`party.color`, hoy a nulo) se curarán entonces.
- La web deberá atribuir la fuente (Wikipedia, CC BY-SA, enlace a la revisión): encaja con el pendiente de atribución del cierre.

## Tareas

Cada una es un commit atómico (tests incluidos, TDD donde toca); ningún cambio de modelo sin los tres sitios.

1. **Modelo** — ERD con las páginas *Bronze polls* y *Silver polls* + `models.py` + migración; `alembic check` limpio; [`data-model.md`](../data-model.md) al día.
2. **Fetch** — `fetch-polls` + tests de URL/parseo de la API con fixture JSON (sin red); matiz de descarga en [`architecture.md`](../architecture.md) y [`ingestor/AGENTS.md`](../../ingestor/AGENTS.md).
3. **Lexer** — `parsers/wikitext.py` + tests.
4. **Adaptador** — `adapters/wikipedia_polls.py` + mapeo de partidos + fixtures recortadas + tests.
5. **Carga** — `loaders/polls.py` + CLI `ingest-polls` + [`docs/ingestor/ingesta.md`](../../docs/ingestor/ingesta.md), con el pase de resolución de `poll.election_id`.
6. **Programación** — job cada 12 h: entrada de cron/launchd documentada en [`environment.md`](../environment.md) y esqueleto de workflow con `schedule:` para cuando haya entorno; test del camino «sin novedades» (no descarga, exit 0).
7. **Ejecución real** — `fetch-polls` + `ingest-polls` en local; cotejo de un puñado de filas contra la página; nueva sección «Sondeos (Wikipedia)» en [`data-sources.md`](../data-sources.md) con formato y rarezas.
8. **Cierre** — plegar lo durable a los docs, `status.md`, plan a `hecho`.

## Flecos y riesgos

- **Licencia**: el texto de Wikipedia es CC BY-SA; la web debe citar la fuente y la revisión. Amplía el pendiente de atribución.
- **Renombrados de página** («2027…», «next…»): `redirects=1` en la API y `--page` cuando toque; el bronce queda pinneado por `revid`. Si la página desaparece, el job de las 12 h falla con exit ≠ 0 (el aviso, de momento, es el log).
- **Identidad de partidos**: el mapeo usa los slugs actuales (`jxcat-junts`, `eaj-pnv`, `u-p-n`); SALF y Aliança.cat se crean. Revisar duplicados cuando exista el 03 de 2026.
- **CIS y reestimaciones**: conviven como filas con `source` literal; si ensucian el gráfico, se filtran en `gold`.
- **Deriva del formato wiki**: plantillas nuevas o celdas raras → warning y a seguir; las fixtures fijan las formas actuales.
- **Cadencia**: 2×/día es lo pedido; los sondeos se publican a cualquier hora, así que entre ejecuciones la web muestra la última foto. Subir la frecuencia es cambiar el cron.
