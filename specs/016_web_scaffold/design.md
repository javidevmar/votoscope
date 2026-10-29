# Diseño — `web_scaffold`

Feature 16 de [`feature_list.json`](../../feature_list.json). Scaffold de `web/`: aplicación Next.js (App Router, TypeScript, pnpm, Tailwind CSS y shadcn/ui) con un BFF obligatorio en `app/api/` que lee las vistas `gold`, rol de Postgres de solo lectura creado por migración y logging por niveles con `LOG_LEVEL` en servidor. Consume el contrato de [`specs/015_delivery_gold/`](../015_delivery_gold/) sin redefinirlo; no cambia el ingestador salvo la migración del rol y sus tests.

## Estado observado al redactar (2026-10-19, local; no congelado)

- `web/` solo contiene `AGENTS.md`. `gold` y su contrato (`docs/db/gold.md`) llegan con la feature 15, que va antes en la cola.
- `web/AGENTS.md`, [`.agents/conventions.md`](../../.agents/conventions.md) y [`.agents/style.md`](../../.agents/style.md) dejan la web «por definir»: esta feature cierra el stack, el gestor, el logging y la estrategia de tests.
- Herramientas locales: **Node v26.5.1** y **pnpm 10.28.0**. Verificado en esa versión de Node: `node --test` ejecuta ficheros `.ts` con el *type stripping* nativo (sin transpilador), descubre `*.test.ts` sin argumentos y **exige extensión explícita `.ts` en los imports relativos** entre módulos TypeScript. No se importan ficheros `.tsx` desde los tests (el *stripping* no transforma JSX): el render se cubre con el smoke manual y las pruebas de los módulos.
- Postgres local en `localhost:5434` (docker-compose; usuario `votoscope` superusuario); `settings.database_url` es la URL del ingestador. El tests del rol viven en el lado pytest (patrón de `test_polls_run.py`: sesión real con skip si no hay base).

## Decisiones

### D1 — Stack: `create-next-app` (Next.js 16, App Router, TypeScript) con **pnpm**, **Tailwind CSS** y **shadcn/ui**

```
pnpm create next-app@latest web --empty --ts --app --eslint --tailwind \
    --no-src-dir --import-alias "@/*" --use-pnpm

cd web
pnpm dlx shadcn@latest init --base-color neutral --css-variables
pnpm dlx shadcn@latest add button card
```

- **App Router + TypeScript**: lo pide el acceptance (Server Components).
- **pnpm**: gestor elegido por el proyecto (10.28.0 local); `pnpm-lock.yaml` versionado y `"packageManager": "pnpm@10.28.0"` en `package.json` para que Corepack fije la versión. Aporta `node_modules` estricto (sin dependencias fantasma), instalación más rápida y menos disco que npm. `engines: { "node": ">=24" }` (el runner de tests necesita el *type stripping* de TS, estable desde Node 24; local hay 26).
- **Tailwind CSS 4 + shadcn/ui**: es el sistema de UI del proyecto. `--tailwind` deja `@tailwindcss/postcss`, `postcss.config.mjs` y `app/globals.css` con `@import "tailwindcss"`; `shadcn init` añade `components.json`, los tokens de tema y `web/lib/utils.ts` (`cn`), y `shadcn add` instala los componentes en `web/components/ui/`. La portada usa `card` y `button` para demostrar el camino completo. Los flags del CLI pueden variar por versión (si `init` pide confirmación, se aceptan los valores por defecto: base neutral y variables CSS); el estado final requerido es `components.json` + `components/ui/` + `lib/utils.ts` + tokens en `globals.css`.
- **`--empty`**: evita la landing de ejemplo; el diseño de las pantallas llega con las features del frontend, sobre estos tokens.
- **ESLint**: se conserva el `eslint.config.mjs` del template (`eslint` + `eslint-config-next`) como puerta de estilo de la web, equivalente al ruff del ingestador.
- Ajuste en `web/tsconfig.json`: `"allowImportingTsExtensions": true` (necesario para los imports con extensión `.ts` de §D8; los docs de Next lo recomiendan al migrar desde Vite).

**Dependencias propuestas (aprobación humana en el gate del spec):**

| Tipo | Paquete | Para qué |
| --- | --- | --- |
| runtime | `next`, `react`, `react-dom` | framework y UI (los fija el template) |
| runtime | `pg` | driver de Postgres (D2) |
| runtime | `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react` | base de shadcn/ui (`cn`, variantes e iconos) |
| runtime | `@radix-ui/react-slot` | primitiva que instala `shadcn add button`; cada componente añadido trae las suyas |
| dev | `typescript`, `@types/node`, `@types/react`, `@types/react-dom` | tipos (los fija el template) |
| dev | `@types/pg` | tipos del driver |
| dev | `eslint`, `eslint-config-next` | lint del template |
| dev | `tailwindcss`, `@tailwindcss/postcss`, `tw-animate-css` | Tailwind 4 y utilidades de animación de shadcn |

Sin framework de tests (runner nativo, D8). Cualquier otra dependencia futura vuelve a pasar por el gate (`.agents/conventions.md`).

### D2 — Driver de Postgres: **`pg`** (node-postgres)

- De-facto estándar, sin etapa de código generado, con `Pool` de conexiones y consultas parametrizadas (`$1`) — en la web solo hay `SELECT`.
- Vale para el Postgres local (TCP, 5434) y para el runtime Node de Vercel con Neon; no ata la web a un proveedor.
- **Tipos de `pg` que hay que mapear** (documentado en `app/api/_lib/gold.ts`): `integer` → `number`; `bigint`/`numeric` → `string` (se convierten con `Number(...)` en las funciones de mapeo); `date` → `Date`. La limpieza queda dentro de `app/api/_lib/gold.ts`: las páginas reciben tipos ya numéricos.

### D3 — Estructura de `web/`

```
web/
├── AGENTS.md            # constitución del frontal para agentes (R15)
├── README.md            # guía de arranque para humanos (R19)
├── .env.example         # DATABASE_URL + LOG_LEVEL (se versiona; credenciales de desarrollo)
├── .env.local           # real, gitignored (ya cubierto por el .gitignore raíz)
├── app/
│   ├── api/             # BFF: única frontera de datos (R2, R4)
│   │   ├── _lib/        # privado, no genera rutas
│   │   │   ├── db.ts    # Pool de pg y queryRows()
│   │   │   ├── gold.ts  # SQL de gold.*, mapeo y funciones de consulta (R2)
│   │   │   └── params.ts # validación de query params
│   │   └── gold/
│   │       ├── latest-election/route.ts
│   │       └── national-results/route.ts
│   ├── globals.css      # Tailwind + tokens de shadcn (R18)
│   ├── layout.tsx       # metadata y lang="es"
│   └── page.tsx         # portada: última elección + resultados nacionales (R3), con Card/Button de shadcn
├── components/
│   └── ui/              # componentes de shadcn (button, card, …; R18)
├── lib/
│   ├── logging.ts       # logger por niveles con LOG_LEVEL (R10–R12)
│   └── utils.ts         # cn() de shadcn (R18)
├── tests/
│   ├── structure.test.ts
│   ├── bff.test.ts
│   ├── logging.test.ts
│   ├── gold_contract.test.ts
│   ├── gold_live.test.ts
│   └── docs.test.ts
├── components.json · postcss.config.mjs
├── next.config.ts · tsconfig.json · eslint.config.mjs · package.json · pnpm-lock.yaml
└── public/ (del template)
```

Sin `src/`: una carpeta menos para una app de este tamaño.

### D4 — BFF obligatorio: `web/app/api/` es la única puerta de datos (R2, R4)

Ninguna página, componente o módulo de `web/lib/` importa `pg`, contiene SQL ni llama a servicios externos. Todo eso vive bajo `web/app/api/`:

- `app/api/_lib/` es privado (no genera rutas): `db.ts` (Pool y `queryRows`), `gold.ts` (SQL, mapeo y funciones de consulta) y `params.ts` (validación de query params).
- `app/api/gold/latest-election/route.ts` y `app/api/gold/national-results/route.ts` son la única superficie HTTP de datos: `GET` devuelve JSON con `Cache-Control: no-store`, valida `electionId` (entero > 0) y traduce cualquier fallo a 500 `{ error: "internal" }` sin filtrar SQL, credenciales ni stack.
- La portada es un Server Component que importa el servicio `_lib/gold.ts` y lo ejecuta en servidor (sin self-fetch). El navegador nunca recibe la conexión: si un componente cliente necesita datos, llama a `/api/*`.
- Un test estructural falla si hay SQL o `pg` fuera de `app/api/`, si una página importa `pg`, si aparece `NEXT_PUBLIC_DATABASE_URL` o si hay Server Actions que sirvan datos.

SQL como constantes exportadas (el test de contrato las lee sin base) + funciones de consulta con mapeo de filas:

```ts
export const SQL_LATEST_ELECTION = `
  SELECT election_id, election_type, election_date, election_name,
         census, null_votes, blank_votes, candidature_votes, valid_votes,
         voters, turnout_pct
  FROM gold.election_summary
  ORDER BY election_date DESC
  LIMIT 1`;

export const SQL_NATIONAL_RESULTS = `
  SELECT party_id, party_slug, party_name, party_color, votes, pct
  FROM gold.result_by_area
  WHERE election_id = $1 AND level = 'national'
  ORDER BY votes DESC`;
```

- Columnas y semántica **verbatim del contrato** ([`specs/015_delivery_gold/design.md`](../015_delivery_gold/design.md), [`docs/db/gold.md`](../../docs/db/gold.md)): `election_summary` da la última general con `order by election_date desc limit 1`; `result_by_area` filtra por `election_id` y `level` (vocabulario cerrado `national|community|province|municipality`). Los `pct` ya vienen calculados; la web **no agrega hechos**.
- Funciones y tipos:

```ts
export type ElectionSummary = {
  electionId: number; electionType: string; electionDate: Date; electionName: string | null;
  census: number; nullVotes: number; blankVotes: number; candidatureVotes: number;
  validVotes: number; voters: number; turnoutPct: number | null;
};
export type NationalResult = {
  partyId: number; partySlug: string; partyName: string; partyColor: string | null;
  votes: number; pct: number | null;
};
export async function getLatestElection(): Promise<ElectionSummary | null>;
export async function getNationalResults(electionId: number): Promise<NationalResult[]>;
export const GOLD_SQL: Readonly<Record<string, string>>;  // { latest_election, national_results }
```

- `party_color` puede ser NULL (fichas sin color curado): la portada usa un color por defecto; `pct` puede ser NULL (sondeos) aunque en resultados no lo sea hoy — los tipos lo contemplan.
- Las pantallas de sondeos (`poll_flat`, `poll_trend`) llegan con las features del frontend sobre este scaffold: se añaden a este mismo servicio y, si el navegador las consume, a un Route Handler bajo `app/api/gold/` (no hay otro sitio con SQL).

### D5 — Conexión: `web/app/api/_lib/db.ts`

```ts
export function getPool(): Pool;                       // DATABASE_URL (error claro si falta); Pool perezoso
export async function queryRows<T>(text: string, params?: unknown[]): Promise<T[]>;
```

- `new Pool({ connectionString, application_name: "votoscope-web" })`; el pool se crea en la primera consulta (no en el import: los tests pueden importar sin base).
- `queryRows` loguea a `debug` el SQL y el número de filas, y a `error` el mensaje del fallo antes de propagar. **Nunca** loguea la URL ni las credenciales (R13).
- La `DATABASE_URL` de la web usa el rol de solo lectura y el formato de `pg` (`postgresql://…`, sin el prefijo `+psycopg` de SQLAlchemy); variable sin `NEXT_PUBLIC_` (R14). Next carga `web/.env.local` en servidor.

### D6 — Logging: `web/lib/logging.ts`, sin dependencias (R10–R12)

```ts
export type LogLevel = "debug" | "info" | "warn" | "error";
export function parseLogLevel(raw: string | undefined): LogLevel;   // desconocido/undefined → "info"
export type LogSink = Pick<typeof console, "log" | "warn" | "error">;
export function createLogger(sink?: LogSink): Logger;               // sink inyectable → tests
export const logger: Logger;                                        // logger del servidor
```

- Formato propio sobre `console`: `2026-10-19T08:00:00.000Z info  [votoscope-web] mensaje`; `debug`/`info` → `console.log`, `warn` → `console.warn`, `error` → `console.error`.
- El nivel efectivo se calcula **en cada llamada** desde `process.env.LOG_LEVEL` (barato y trivial de testear; `parseLogLevel` hace el fallback a `info`, R12). Nada de `NEXT_PUBLIC_`: es logging de servidor.
- No hay logging en cliente (no hay componentes de cliente todavía).

### D7 — Rol de solo lectura `votoscope_web`, creado por migración (R5–R9)

Migración nueva en el ingestador (sin `--autogenerate`: los roles no están en la metadata), `down_revision` = la migración de las vistas `gold` de la feature 15:

```python
def upgrade() -> None:
    op.execute("CREATE ROLE votoscope_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE")
    op.execute("GRANT USAGE ON SCHEMA gold TO votoscope_web")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA gold TO votoscope_web")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO votoscope_web")

def downgrade() -> None:
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA gold REVOKE SELECT ON TABLES FROM votoscope_web")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA gold FROM votoscope_web")
    op.execute("REVOKE USAGE ON SCHEMA gold FROM votoscope_web")
    op.execute("DROP ROLE votoscope_web")
```

- **Privilegios por defecto**: `GRANT SELECT ON ALL TABLES` solo cubre las vistas existentes; sin `ALTER DEFAULT PRIVILEGES` las vistas que añadan features futuras (nuevas migraciones del ingestador, ejecutadas por el rol propietario `votoscope`) nacerían sin `SELECT` para la web. El `ALTER DEFAULT PRIVILEGES` (sin `FOR ROLE`, aplica al rol que ejecuta las migraciones) lo evita. Limitación documentada: si en otro entorno las migraciones corren con un propietario distinto, sus privilegios por defecto son otros.
- **Contraseña**: la migración crea el rol **sin contraseña** (nunca credenciales en ficheros versionados, R9). Local (una vez, documentado en `web/AGENTS.md`):

  ```bash
  docker compose exec db psql -U votoscope -d votoscope \
    -c "ALTER ROLE votoscope_web PASSWORD 'votoscope_web'"
  ```

  Producción: el rol lo crea la misma migración y la contraseña se fija en el panel del proveedor (Neon) / `DATABASE_URL` como secreto de Vercel (topología de la feature 15). `web/.env.example` lleva la credencial **de desarrollo** (`votoscope_web:votoscope_web@localhost:5434`), como el `.env.example` del ingestador.
- Si el rol ya existiera (entorno manipulado), `CREATE ROLE` falla y se resuelve con `DROP ROLE` antes de migrar; no se añaden guardas condicionales.
- **PENDIENTE DE APROBACIÓN**: el nombre del rol es `votoscope_web` (alternativa descartada: `web_readonly`, menos coherente con `votoscope`).

### La regla de oro: qué toca el rol y qué no

El rol **no es un objeto del modelo** (no es tabla ni vista): la regla ERD ↔ `models.py` ↔ migración no le aplica en sus dos primeros sitios.

- **No toca `docs/db/schema.drawio`**: no hay entidad que dibujar; el ERD documenta estructura, no seguridad.
- **No toca `ingestor/src/ingestor/models.py`**: no hay `Table` declarada; autogenerate no refleja roles, así que `alembic check` sigue sin drift sin tocar `env.py`.
- **Toca solo la migración** (`ingestor/alembic/versions/<rev>_web_readonly_role.py`): `data-model.md` dice que las migraciones son «la fuente de verdad de la base de datos», y el rol es parte de la base de datos. Su verificación no es el ERD sino el test live (`ingestor/tests/test_web_role.py`) más el propio `alembic upgrade head`.

### D8 — Estrategia de tests de la web (fija `conventions.md`, R16)

Dos runners, un reparto por capa:

| Capa | Runner | Dónde | Por qué |
| --- | --- | --- | --- |
| Web (queries, logging, estructura, docs de la web) | `node --test` (nativo de Node ≥ 24) | `web/tests/*.test.ts` | `--test` ejecuta `.ts` con *type stripping*, sin framework ni transpilador (verificado en Node v26.5.1) |
| Base de datos (rol, grants, migración) | pytest (el del repo) | `ingestor/tests/test_web_role.py` | La BD y sus migraciones son del ingestador; se reutiliza el patrón de sesión real con skip |

- Script: `"test": "node --env-file-if-exists=.env.local --test"`; `--env-file-if-exists` carga `.env.local` cuando existe y no falla si no (los tests *live* se saltan sin `DATABASE_URL`).
- Regla de imports en `web/`: **extensión explícita** (`.ts`/`.tsx`) en imports relativos y por alias — es lo que exige el runner nativo de Node; en el resto, TypeScript normal. `tsconfig.json` gana `allowImportingTsExtensions`.
- Herméticos (sin base): `structure.test.ts` (R1, R4, R14, R18: estructura, BFF, sin SQL/`pg` fuera de `app/api/`), `bff.test.ts` (R2, R4: cada `route.ts` exporta `GET`, declara `force-dynamic`, responde `no-store`, no contiene SQL y valida `electionId`), `gold_contract.test.ts` (R2: solo `SELECT`, solo `gold.*`, vistas del contrato, `order by`/`limit`/`level = 'national'`/`$1`), `logging.test.ts` (R10–R12), `docs.test.ts` (R15–R17, R19).
- Live (se saltan sin `DATABASE_URL`, sin base o sin datos, con `t.skip(...)`): `gold_live.test.ts` ejecuta las funciones del servicio real contra `gold` en la base local y verifica: la última elección coincide con `max(election_date)` de la propia vista, tipado numérico, resultados nacionales ordenados por votos con `pct` en rango, y —capturando `console` con `LOG_LEVEL=debug`— que la salida no contiene la URL ni la contraseña (R13).
- `init.sh` gana una sección web: si `web/node_modules` existe, `pnpm test` y `pnpm lint`; si no, `warn` y se omite (mismo criterio que la comprobación del Postgres).
- El render de la portada no se testea con el runner nativo (no puede importar `.tsx`): se verifica con el smoke de `pnpm dev` documentado en `progress/impl_web_scaffold.md`; los tests de renderizado llegarán cuando la UI lo pida (se revisará el runner en un spec futuro si hace falta).

### D9 — Página de inicio (R3)

`app/page.tsx`, Server Component asíncrono:

```tsx
import { getLatestElection, getNationalResults } from "@/app/api/_lib/gold.ts";

export const dynamic = "force-dynamic";

export default async function Home() { … }
```

- `force-dynamic`: sin él, `next build` prerrenderizaría la portada y exigiría la base en el build; con datos que cambian con cada ingesta, la página se renderiza por petición.
- Estado vacío («Sin datos») si no hay elecciones con hechos. `turnout_pct` y `party_color` se pintan con fallback (`—`, color por defecto).
- Sin manejo especial si la base cae: en desarrollo Next muestra el error; la tolerancia a fallos llega con las pantallas del MVP.

### D10 — Documentos (R15–R19)

- **`web/AGENTS.md`** (constitución del frontal para agentes): se reescriben «Estado» y «Reglas» y se añaden secciones de estructura, BFF (`app/api/` como única frontera de datos), comandos (`pnpm install`, `pnpm dev` en `http://localhost:3000`, `pnpm test`, `pnpm lint`, `pnpm build`, `pnpm dlx shadcn@latest add <componente>`), configuración (`web/.env.example` → `.env.local`; `DATABASE_URL` de `votoscope_web` y `LOG_LEVEL`), rol (privilegios, contraseña local con `ALTER ROLE`, migración que lo crea), logging, tests y dependencias aprobadas. Puntero a [`docs/db/gold.md`](../../docs/db/gold.md).
- **`web/README.md`** (guía de arranque para humanos, R19): qué es el frontal; requisitos (Node ≥ 24, pnpm 10.28 con Corepack); `pnpm install` y `.env.example` → `.env.local`; comandos `dev`/`build`/`start`/`lint`/`test`; estructura de carpetas y BFF (`app/api/`); rol `votoscope_web` y `ALTER ROLE` local; Tailwind + shadcn (`components.json`, `components/ui/`, cómo añadir componentes); tests herméticos y live; enlaces al contrato [`docs/db/gold.md`](../../docs/db/gold.md) y a [`AGENTS.md`](AGENTS.md). No repite las reglas de proceso de AGENTS.
- **`.agents/conventions.md`**: logging de la web (implementación), regla del BFF (`app/api/` como única frontera de datos), dependencias de la web (pnpm + lista aprobada) y tests (runner nativo, `web/tests/`, herméticos + live, `init.sh`).
- **`.agents/architecture.md`**: el punto del frontend deja de decir «Pendiente de scaffold» y describe el scaffold y el rol.
- **`.agents/environment.md`**: la sección Frontend, igual (comandos locales y `.env.local`).
- Fuera de alcance: `feature_list.json` (lo actualiza el leader) y `.agents/status.md`/README **raíz** (feature 17).

## Archivos

| Acción | Archivo |
| --- | --- |
| crear | `web/` — scaffold Next.js (configuración, `app/`, `components/`, `public/`, `package.json`, `pnpm-lock.yaml`) |
| crear | `web/.env.example` — `DATABASE_URL` (rol de solo lectura) y `LOG_LEVEL` |
| crear | `web/app/api/_lib/db.ts` · `web/app/api/_lib/gold.ts` · `web/app/api/_lib/params.ts` (BFF, R2/R4) |
| crear | `web/app/api/gold/latest-election/route.ts` · `web/app/api/gold/national-results/route.ts` (BFF, R4) |
| crear | `web/lib/logging.ts` |
| crear | `web/tests/structure.test.ts` · `bff.test.ts` · `logging.test.ts` · `gold_contract.test.ts` · `gold_live.test.ts` · `docs.test.ts` |
| modificar | `web/app/layout.tsx` · `web/app/page.tsx` · `web/tsconfig.json` · `web/package.json` (scripts, engines) |
| modificar | `web/AGENTS.md` (constitución del frontal) |
| crear | `web/README.md` — guía de arranque (R19) |
| crear | `ingestor/alembic/versions/<rev>_web_readonly_role.py` — migración del rol (D7) |
| crear | `ingestor/tests/test_web_role.py` — R5–R9 |
| modificar | `.agents/conventions.md` · `.agents/architecture.md` · `.agents/environment.md` |
| modificar | `init.sh` — sección 5 (web), renumerando las siguientes |
| crear | `progress/impl_web_scaffold.md` — evidencia del smoke y trazabilidad R ↔ test |

## Firmas nuevas

- `web/lib/logging.ts`: `LogLevel`, `parseLogLevel(raw)`, `LogSink`, `Logger`, `createLogger(sink?)`, `logger`.
- `web/app/api/_lib/db.ts`: `getPool()`, `queryRows<T>(text, params?)`.
- `web/app/api/_lib/gold.ts`: `ElectionSummary`, `NationalResult`, `SQL_LATEST_ELECTION`, `SQL_NATIONAL_RESULTS`, `GOLD_SQL`, `getLatestElection()`, `getNationalResults(electionId)`.
- `web/app/api/_lib/params.ts`: `parseElectionId(raw: string | null): number` (lanza `RangeError` si no es entero > 0).
- `web/app/api/gold/latest-election/route.ts` y `national-results/route.ts`: `GET(request: Request): Promise<Response>`, `dynamic = "force-dynamic"`.
- Migración: `upgrade()` / `downgrade()` con los `op.execute` de D7. Sin excepciones nuevas en el ingestador (no toca `IngestError`).
- Sin cambios en `models.py`, ni en `gold.py`, ni en el CLI del ingestador.

## Tests (mapa R ↔ test)

| Test | Cubre | Qué fija |
| --- | --- | --- |
| `web/tests/structure.test.ts` | R1, R4, R14, R18 | scripts y deps aprobadas en `package.json` (`pnpm-lock.yaml`, sin `package-lock.json`); `app/layout.tsx` + `app/page.tsx`; existen los Route Handlers del BFF; page importa `@/app/api/_lib/gold.ts` y un componente de `@/components/ui/`, declara `force-dynamic` y no es cliente; `lib/` sin `"use client"`; **SQL y `pg` solo bajo `app/api/`**; sin `NEXT_PUBLIC_DATABASE_URL`; `.env.example` con el rol de solo lectura; `components.json`, `components/ui/`, `lib/utils.ts` y tokens de Tailwind en `globals.css` |
| `web/tests/bff.test.ts` | R2, R4 | cada `route.ts` exporta `GET`, declara `force-dynamic`, responde `Cache-Control: no-store`, no contiene SQL ni importa `pg`; `params.ts` valida `electionId` (`1` ok; `null`, `0`, `-1`, `abc` → `RangeError`) |
| `web/tests/gold_contract.test.ts` | R2 | cada SQL es un único `SELECT`, solo `gold.*`, vistas del contrato de `docs/db/gold.md`, con `order by election_date desc`/`limit 1` y `level = 'national'`/`$1` |
| `web/tests/gold_live.test.ts` | R2, R3, R13 | servicio real contra `gold` local (última elección = `max(election_date)`; nacional ordenado con `pct` en rango); consola capturada con `LOG_LEVEL=debug` sin URL ni contraseña |
| `web/tests/logging.test.ts` | R10, R11, R12 | niveles y formato con sink inyectado; filtrado por `LOG_LEVEL`; `debug`→`log`, `warn`→`warn`, `error`→`error`; `undefined`/valor inválido → `info` |
| `web/tests/docs.test.ts` | R15, R16, R17, R19 | subcadenas estables de `web/AGENTS.md` (`votoscope_web`, `app/api/`, `pnpm test`, `node --test`, `LOG_LEVEL`, `ALTER ROLE`, `docs/db/gold.md`) y de `conventions.md` (`node --test`, `web/tests`, `pnpm`, `app/api/`, sin «se decidirá en su scaffold»); `architecture.md`/`environment.md` sin «Pendiente de scaffold» y con los comandos de la web; `web/README.md` con requisitos, `pnpm dev`, `.env.local`, `votoscope_web`, `app/api/`, `shadcn` y `docs/db/gold.md` |
| `ingestor/tests/test_web_role.py` | R5, R6, R7, R8, R9 | el fuente de la migración no contiene credenciales; live (skip sin base/rol/vistas): atributos del rol, `USAGE`+`SELECT` en las seis vistas, privilegios por defecto en `pg_default_acl`, y denegación (`silver`/`bronze` sin acceso, sin escritura ni `CREATE` en `gold`) |

## init.sh (delta)

Sección nueva tras la del ingestador (las siguientes se renumeran):

```bash
echo ""
echo "── 5. Web: tests y lint (si node_modules existe) ───────"

if [ ! -d web ]; then
  warn "Falta la carpeta web/; se omite la verificación de la web"
elif [ ! -d web/node_modules ]; then
  warn "web/node_modules no existe; se omite pnpm test (cd web && pnpm install)"
else
  if (cd web && pnpm test --silent); then
    ok "pnpm test: tests de la web pasan"
  else
    fail "pnpm test: hay tests rotos en web/"
    EXIT_CODE=1
  fi
  if (cd web && pnpm lint --silent); then
    ok "pnpm lint"
  else
    fail "pnpm lint con errores"
    EXIT_CODE=1
  fi
fi
```

## Alternativas descartadas

1. **Vitest/Jest/`tsx` como runner de tests**: dependencias extra para algo que `node --test` cubre sin transpilador (verificado en Node v26.5.1). Si en el futuro los tests necesitan JSX o mocking rico, se revisará con su spec.
2. **ORM (Prisma, Drizzle) o query builder**: el contrato ya es SQL de vistas; un ORM añade una segunda definición del esquema, código generado y dependencias, sin beneficio para `SELECT`s de una tabla/vista.
3. **`postgres` (postgres.js) o `@neondatabase/serverless` como driver**: `pg` es el estándar mantenido, funciona en local y en el runtime Node de Vercel. El driver serverless de Neon solo sería necesario en runtime edge: decisión futura si se adopta edge.
4. **Server Components leyendo PostgreSQL directamente (sin BFF)**: descartado por regla del proyecto; el BFF concentra el acceso a datos y servicios externos en `app/api/`, deja el navegador sin acceso a la base y hace verificable la frontera con un test estructural. Coste aceptado: una capa de módulos más (sin self-fetch). **Server Actions para datos**: quedan fuera de `app/api/` y de la frontera del BFF; descartadas explícitamente (R4).
5. **Contraseña del rol en la migración** (literal o interpolada de una variable de entorno): secreto versionado o migración que depende de un secreto; se resuelve con `ALTER ROLE` por entorno (R9).
6. **`GRANT SELECT` enumerando las seis vistas una a una**: lista que envejece con cada vista nueva; `ON ALL TABLES` + `ALTER DEFAULT PRIVILEGES` (R7) cubre el presente y el futuro.
7. **Página estática (build-time)**: `next build` exigiría la base de datos; `force-dynamic` la renderiza por petición, coherente con datos que cambian con la ingesta.
8. **`create-next-app` con la plantilla por defecto (landing de ejemplo)**: ruido; `--empty` deja el mínimo y el sistema de UI (Tailwind + shadcn) se configura aparte con el CLI oficial.
9. **Ubicar los tests de la web en `ingestor/tests/` (pytest)**: pytest no ejecuta los módulos TS de la web; el reparto por capa (D8) queda fijado en `conventions.md`.
10. **Poner las consultas en cada página (o en `app/`) en vez de `app/api/_lib/gold.ts`**: la regla «un único sitio con SQL, bajo `app/api/`» hace trivial el test de contrato (R2) y la auditoría de la frontera de datos (R4).
11. **`src/` dir**: prefijo sin valor para esta app; menos profundidad de rutas.
12. **npm como gestor de paquetes**: viene con Node, pero el proyecto adopta pnpm (lockfile único, `node_modules` estricto y menos disco); `package-lock.json` no se versiona.

## Nota de riesgo

- Los imports con extensión `.ts` son requisito del runner nativo de Node; Next los resuelve (rutas literales) y `allowImportingTsExtensions` los hace válidos para TypeScript — los docs de Next lo recomiendan en su guía de migración desde Vite. Si aun así apareciera un aviso de bundling de `pg`, la salida es una línea de `serverExternalPackages: ["pg"]` en `next.config.ts`.
- `shadcn init` puede pedir confirmación o escribir los tokens con nombres distintos según la versión del CLI; el test estructural (R18) fija el estado mínimo y el `implementer` adapta los flags, no el resultado.
- El BFF evita el self-fetch de los Server Components a su propia API (URL absoluta, cookies, latencia): la página importa el servicio y los Route Handlers son para consumidores cliente. Los errores de las rutas se enmascaran (`500 { error: "internal" }`) y el detalle se loguea en servidor.
- `init.sh` omite los tests de la web (con `warn`) si no hay `node_modules`; el resto del arnés no cambia y la feature no toca `ingestor/` salvo migración y tests.

## Interfaz para las features siguientes

- **Pantallas del MVP**: se añaden bajo `app/` como Server Components y sus consultas en el servicio del BFF (`app/api/_lib/`, misma puerta). Si un componente cliente las consume, se añade un Route Handler bajo `app/api/gold/`. El mapeo pantalla ↔ vista está en [`docs/db/gold.md`](../../docs/db/gold.md).
- **Fallbacks**: `party_color` y `municipality_name` pueden ser NULL; `pct`/`seats_*` de sondeos pueden ser NULL (hueco en la serie); `poll_trend` ya llega ordenada.
- **Vistas nuevas de `gold`**: no necesitan migración de rol (privilegios por defecto, R7) y se leen con las mismas convenciones; si falta un dato, la vista se añade en el ingestador (ERD ↔ modelos ↔ migración), nunca se lee `silver` desde la web.
- **Feature 17** (README raíz/atribución) documentará el arranque completo del proyecto enlazando a `web/README.md`; no depende de ficheros nuevos de esta feature.
