# Diseño — `close_minor`

Feature 17. Cierre del repositorio: **README** (qué es el proyecto y cómo levantarlo), **atribución** de las fuentes (infoelectoral y Wikipedia CC BY-SA con enlace a la revisión) y **pasada final de estado y coherencia** (`.agents/status.md` y documentos de contexto). Es la última feature de la entrega (orden de la cola: 15 `delivery_gold` → 16 `web_scaffold` → 17 `close_minor`), así que se espera ejecutarla con `gold` y `web/` ya entregados; la sección web del README es condicional a la existencia del scaffold (R5).

Esta feature **no añade código de aplicación**: no hay firmas nuevas, ni excepciones nuevas, ni cambios en `ingestor/src/` ni `web/`. Los artefactos son documentos y los tests que los fijan. **No toca el modelo de datos** (sin cambios en `docs/db/schema.drawio`, `models.py` ni Alembic; la regla de oro no aplica). Sin dependencias nuevas.

## Archivos

| Acción | Archivo |
| --- | --- |
| reescribir | `README.md` — de stub (título + una línea en inglés) a README completo en español (R1–R9) |
| modificar | `.agents/status.md` — pasada de estado final (R10) |
| modificar | `.agents/architecture.md` — puerto `5433`→`5434`, oro y web en presente (R11, R12) |
| modificar | `.agents/environment.md` — sección «Frontend» al día (R11) |
| modificar | `ingestor/AGENTS.md` — retirar el «## Pendiente» con las vistas `gold` (R11) |
| modificar | `web/AGENTS.md` — «Estado» al día (R11) |
| modificar | `ingestor/.env.example` — `5433`→`5434` (R12) |
| modificar | `docker-compose.yml` — comentario del puerto `5433`→`5434` (solo comentario; el mapeo ya es `5434:5432`) (R12) |
| crear | `ingestor/tests/test_close_minor.py` — tests de documentos (R1–R12) |
| crear | `progress/impl_close_minor.md` — trazabilidad R ↔ test y evidencia (convención del arnés; no es artefacto del acceptance) |

Las features 15 y 16 ya habrán dejado al día parte de estos documentos (p. ej. 16 actualiza `web/AGENTS.md` y `.agents/conventions.md`): la pasada **verifica y corrige solo lo que siga obsoleto**, con diff mínimo (R11). Si algo no cuadra y no está claro el texto correcto, se para y se documenta.

## README — estructura y anclajes (R1–R9)

Estructura fija (los tests de documentos comprueban las subcadenas marcadas; el texto exacto lo redacta el implementer):

````markdown
# Votoscope

Agregador de resultados electorales de España.

## Qué es

Votoscope convierte los resultados que publica el Ministerio del Interior en
datos normalizados consultables. MVP: las últimas elecciones generales
(Congreso), con resultados por mesa. Pipeline bronce → plata → oro (esquemas
`silver` y `gold`) en `ingestor/` (Python, PostgreSQL) y una web Next.js que lee
`gold` en servidor. `data/raw/` (bronce) no se versiona.

## Requisitos

- Docker (con Compose)
- uv
- Python 3.12 o superior (lo gestiona uv)

## Puesta en marcha

1. Base de datos (Postgres 18 en `localhost:5434`):

   ```sh
   docker compose up -d --wait
   ```

2. Ingestador:

   ```sh
   cd ingestor
   uv sync
   uv run alembic upgrade head
   ```

3. Verificación:

   ```sh
   uv run pytest
   ```

   Para sobrescribir configuración: copiar `ingestor/.env.example` a `ingestor/.env`.

## Datos

- Resultados (portal infoelectoral → `data/raw/congreso/{código}/`, no versionado):
  descargar el ZIP MESA del proceso y descomprimirlo (detalle en `.agents/data-sources.md`).
- Gazetteer INE → `refs/ine/`.
- Carga:

  ```sh
  uv run ingestor load-geography
  uv run ingestor ingest ../data/raw/congreso
  uv run ingestor fetch-polls
  uv run ingestor ingest-polls
  ```

## Web

- `cd web` + comando de desarrollo del scaffold (`npm run dev` y análogos); lee
  las vistas `gold` en servidor. Ver `web/AGENTS.md`.

## Documentación

- `AGENTS.md` (índice del repo), `.agents/` (docs de contexto: arquitectura,
  modelo de datos, fuentes, convenciones…), `docs/ingestor/ingesta.md`
  (comandos y carga), `docs/db/schema.drawio` (ERD), `specs/` (specs por feature).

## Fuentes y atribución

- **Resultados electorales**: portal infoelectoral del Ministerio del Interior
  (`https://infoelectoral.interior.gob.es`); los ficheros `.DAT` cargados son
  copias locales de sus descargas.
- **Sondeos**: página «Opinion polling for the 2026 Spanish general election» de
  Wikipedia (en), reutilizada bajo licencia **CC BY-SA**; revisión usada:
  `https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2026_Spanish_general_election&oldid={revid}`.
  Cada snapshot guarda su `revision_id` y cada carga se verifica en
  `docs/ingestor/polls-run.md`.
````

Notas de redacción:

- La sección «Web» se incluye porque la feature 16 se ejecuta antes (orden de la cola). Si al implementar no existiera scaffold, se omite y el test condicional se salta: **no se inventan comandos**.
- El README enlaza solo lo que se mantiene vivo y resuelve (R9); los enlaces relativos se comprueban.
- La revisión de Wikipedia que se cite es la usada por los datos locales (la misma que documentan `.agents/data-sources.md` y `docs/ingestor/polls-run.md`); si se hizo un `fetch-polls` posterior, se cita la nueva.

## Pasada de estado y coherencia (R10–R12)

Puntos obsoletos detectados al redactar este spec (a verificar y corregir; alguno puede haberlo resuelto ya la 15/16):

| Documento | Ahora dice | Debe quedar |
| --- | --- | --- |
| `.agents/status.md` | «Actualizado: 2026-10-18»; specs 10–14 «listos para aprobar»; transversal: logging «pendiente en la web» | Fecha nueva; 15–17 en «Hecho» (vistas `gold`, web, README/atribución); cola pendiente: 18 `source_norm` (puntero a `feature_list.json`); sin las frases obsoletas |
| `.agents/architecture.md` | mapa: «Postgres 18 local (host: 5433)»; oro «Pendientes de crear»; web «Pendiente de scaffold» | `5434`; oro creado (vistas `gold`); web scaffoldada (con `web/AGENTS.md`) |
| `.agents/environment.md` | Frontend: «Pendiente de scaffold» | Cómo se levanta la web (comando del scaffold) + rol de solo lectura |
| `ingestor/AGENTS.md` | «## Pendiente — - Vistas `gold`.» | Sección retirada (nada pendiente en el ingestador tras la 15) |
| `web/AGENTS.md` | «Estado: Aún no hay scaffold…» | Estado real (app scaffoldada; cómo correrla) |
| `ingestor/.env.example` | `DATABASE_URL=…@localhost:5433/votoscope` | `localhost:5434` (copiarlo a `.env` debe funcionar) |
| `docker-compose.yml` | comentario «5433 because …» | comentario acorde al mapeo `5434:5432` |

El resto de docs de contexto (`AGENTS.md` raíz, `.agents/specs.md`, `.agents/conventions.md`, `.agents/data-model.md`, `docs/ingestor/*.md`) no tiene afirmaciones obsoletas conocidas; se revisan de pasada y **solo se toca lo que esté desactualizado**.

## Tests — `ingestor/tests/test_close_minor.py` (R1–R12)

Solo lectura de ficheros del repo: sin red, sin base de datos, sin tocar `ingestor/src/`. Patrón de los tests de documentos del repo (features 9–11): subcadenas estables que fijan el contrato sin acoplarse al texto completo.

Helpers:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]

def _read(*parts: str) -> str:  # (REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8")

def _relative_links(text: str) -> list[str]:
    """Targets de '](target)' que no son http(s)/mailto/ancla, sin fragmento."""
```

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `test_readme_project_summary` | R1 | `Votoscope`, `resultados electorales`, `España`, `Congreso`, `resultados por mesa`, `bronce`, `plata`, `oro`, `silver`, `gold`, `Next.js` |
| `test_readme_prerequisites` | R2 | `Docker`, `uv`, `Python` |
| `test_readme_setup` | R3 | `docker compose up -d --wait`, `5434`, `cd ingestor`, `uv sync`, `uv run alembic upgrade head`, `uv run pytest`; y orden (`index` creciente) `docker compose up -d --wait` < `uv sync` < `uv run alembic upgrade head` |
| `test_readme_data` | R4 | `data/raw/congreso`, `refs/ine`, `uv run ingestor load-geography`, `uv run ingestor ingest`, `uv run ingestor fetch-polls`, `uv run ingestor ingest-polls` |
| `test_readme_web_if_scaffolded` | R5 | `pytest.skip` si no existe `web/package.json`; si existe: `web/`, `gold` y uno de `npm run dev` / `pnpm dev` / `bun run dev` / `yarn dev` / `next dev` (el comando real lo fija el scaffold de la 16) |
| `test_readme_attribution` | R6, R7 | `infoelectoral.interior.gob.es`, `Ministerio del Interior`, `en.wikipedia.org`, `Opinion polling for the 2026 Spanish general election`, `CC BY-SA`, `oldid=` |
| `test_readme_docs_links` | R8 | `AGENTS.md`, `.agents/`, `docs/ingestor/ingesta.md` |
| `test_readme_relative_links_resolve` | R9 | `_relative_links(README)`: cada target resuelto contra `REPO_ROOT` existe (fichero o carpeta); ninguna ancla/URL externa se comprueba |
| `test_status_document_current` | R10 | `.agents/status.md`: `re.search(r"Actualizado: \d{4}-\d{2}-\d{2}")`, `README`, `gold`, `source_norm`; y **no** contiene `listos para aprobar` ni `pendiente en la web` |
| `test_context_docs_coherent` | R11 | `.agents/architecture.md` sin `Pendiente de scaffold`, `Pendientes de crear`; `.agents/environment.md` sin `Pendiente de scaffold`; `ingestor/AGENTS.md` sin `Vistas \`gold\`.`; `web/AGENTS.md` sin `Aún no hay scaffold` |
| `test_port_references` | R12 | `5433` ausente en `README.md`, `.agents/architecture.md`, `ingestor/.env.example` y `docker-compose.yml`; `5434` presente en `README.md` y `ingestor/.env.example` |

Detalles que fijan el contrato:

- Las subcadenas se buscan en el texto completo (como en `test_polls_schedule.py`); el reviewer valida el resto (prosa, orden de secciones, exactitud del enlace a la revisión).
- `test_readme_setup` es el único que comprueba orden: los tres comandos de puesta en marcha (base → dependencias → migraciones) deben aparecer en ese orden en el README; el resto de subcadenas son de presencia.
- `test_readme_web_if_scaffolded` se salta en la CI de ramas previas a la 16 y corre en local/CI una vez la 16 está mergeada; cuando la 16 fije su gestor de paquetes y su comando, el implementer ajusta la tupla del test si hace falta (documentado en `progress/impl_close_minor.md`).
- El enlace a la revisión de Wikipedia (`oldid=`) no se compara con un revid concreto: cambia con cada `fetch-polls`. El reviewer comprueba que coincide con la revisión cargada en `silver`/documentada en `polls-run.md`.
- Los tests no escriben nada del repo: el contrato es «los documentos dicen X», no mutar el estado.

## Decisiones

- **Un solo README, en la raíz y en español**: es la portada del repositorio (GitHub), el idioma de los docs ([`conventions.md`](../../.agents/conventions.md)) y el `readme` de `ingestor/pyproject.toml` no necesita otro (`web/` tiene `web/AGENTS.md`).
- **Comandos reales, no un «getting started» ideal**: el README documenta el flujo que existe (docker-compose + uv + alembic + CLI) y advierte de lo que no se versiona (`data/raw/`, `refs/`), que es donde un clon recién bajado se atasca.
- **Atribución en el README (y ya en `.agents/data-sources.md`)**: la licencia CC BY-SA de Wikipedia obliga a citar fuente y enlazar la revisión; el README lo hace para el visitante y `data-sources.md` mantiene el detalle operativo.
- **La pasada de estado toca solo lo obsoleto**: las features 15/16 ya actualizan lo suyo; reescribir documentos enteros multiplicaría el diff sin necesidad. El contrato son las frases prohibidas y los datos corregidos (puerto, presentes).
- **Tests de subcadenas + resolución de enlaces relativos**: patrón del repo (features 10–11) para fijar documentos; la resolución de enlaces es la única comprobación «semántica» (un README con enlaces roto no cumple R8/R9) y no necesita dependencias.
- **El puerto `5434` se corrige también en `.env.example` y en el comentario de `docker-compose.yml`**: copiar el ejemplo a `.env` con `5433` rompería la conexión; es documentación de entorno desactualizada, no un cambio funcional.
- **R5 condicional**: la sección web depende del scaffold de la 16; el spec no puede fijar su comando de antemano, así que el test se salta sin `web/package.json` y exige comando+`gold` cuando existe.

## Alternativas descartadas

1. **README en inglés o bilingüe**: los docs del repo son en español y hay un solo público; mantener dos versiones es duplicar la verdad para este MVP.
2. **Añadir un fichero `LICENSE`**: el acceptance pide atribución de las fuentes (que queda en el README y ya en `.agents/data-sources.md`), no la licencia del código, que es una decisión del usuario y no se inventa.
3. **`web/README.md` propio para el frontend**: duplicaría la información; `web/AGENTS.md` ya describe la app y el README raíz enlaza y documenta cómo correrla.
4. **Linter de markdown (markdownlint/pytest-markdown)**: dependencia nueva sin consentimiento para lo que hace un test propio con la stdlib (subcadenas + enlaces).
5. **Un test que renderice el README** (markdown → HTML): no aporta sobre la resolución de enlaces y las subcadenas; añade dependencia y superficie.
6. **Reescribir los docs de contexto completos**: la pasada de cierre corrige lo obsoleto; los docs ya están al día por las features anteriores y un rewrite perdería detalle probado por sus tests (p. ej. `test_docs_data_sources`).
7. **Congelar el revid de Wikipedia en el test**: cambia con cada sincronización 2×/día; el test exige el enlace (`oldid=`), el reviewer contrasta el número con la carga real.
8. **Instalar el cron/launchd desde esta feature**: la 10 ya documenta la operación; aquí es README y coherencia de docs, no operación de la máquina (y sería un cambio fuera del acceptance).

## Notas

- Orden de la cola: 15 → 16 → 17; si al implementar la 16 no estuviera cerrada (p. ej. se aprueba e implementa 17 antes), la sección web se omite y se deja constancia en `progress/impl_close_minor.md`.
- Las subcadenas del README fijan el mínimo; la calidad (prosa, claridad del «cómo levantarlo») la revisa el reviewer contra este diseño.
- `progress/impl_close_minor.md` es de la sesión (trazabilidad R ↔ test); no es un artefacto del acceptance ni lo leen los tests.
