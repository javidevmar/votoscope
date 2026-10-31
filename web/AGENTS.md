# AGENTS.md — web

Contexto del frontend. Antes de tocar nada, lee también el `AGENTS.md` de la raíz del repo.

Proceso: toda feature con `sdd: true` en [`../feature_list.json`](../feature_list.json) pasa por su spec en `../specs/<name>/` antes de tocar código; ver [`../AGENTS.md`](../AGENTS.md) y [`../.agents/specs.md`](../.agents/specs.md).

## Qué es

Frontend del agregador, en Next.js (App Router). Consume las vistas del esquema `gold` a través de un **BFF obligatorio** en `app/api/`: toda consulta a PostgreSQL o a servicios externos vive ahí y el navegador nunca recibe credenciales ni SQL. Las páginas se renderizan en servidor (Server Components).

## Estado

Scaffold hecho: Next.js 16 (App Router, TypeScript), pnpm 10.28, Tailwind CSS 4 y shadcn/ui. La portada demuestra el camino completo (Server Component → servicio del BFF → vistas `gold` → HTML). El contrato pantalla ↔ vista está en [`../docs/db/gold.md`](../docs/db/gold.md).

## Estructura

- `app/` — App Router: `layout.tsx`, `page.tsx` (portada) y `globals.css` (Tailwind + tokens).
- `app/api/` — **BFF**, única frontera de datos:
  - `app/api/_lib/db.ts` — `getPool()` y `queryRows()` con `pg`.
  - `app/api/_lib/gold.ts` — único sitio con SQL: constantes de `gold.*`, mapeo de filas y `getLatestElection()` / `getNationalResults()`.
  - `app/api/_lib/params.ts` — validación de query params.
  - `app/api/gold/latest-election/route.ts` y `app/api/gold/national-results/route.ts` — Route Handlers `GET` con `Cache-Control: no-store`.
- `components/ui/` — componentes de shadcn; `lib/utils.ts` (`cn`).
- `lib/logging.ts` — logger de servidor por niveles.
- `tests/` — tests con `node --test` (ver abajo).

## Comandos

```bash
pnpm install          # dependencias
pnpm dev              # http://localhost:3000
pnpm build            # build de producción (sin base: la portada es force-dynamic)
pnpm start            # servir el build
pnpm test             # node --test (carga .env.local si existe)
pnpm lint             # ESLint (eslint-config-next)
pnpm dlx shadcn@latest add <componente>   # añadir UI de shadcn
```

## Configuración

- Copiar `.env.example` a `.env.local` (gitignored). Next carga `.env.local` solo en servidor.
- `DATABASE_URL` usa el rol de solo lectura `votoscope_web` (`postgresql://…`, sin `+psycopg`). **Nunca** `NEXT_PUBLIC_DATABASE_URL`: la credencial no llega al cliente.
- `LOG_LEVEL` (`debug`/`info`/`warn`/`error`; por defecto `info`) fija el nivel del logging de servidor.

## Rol de base de datos

- `votoscope_web` lo crea la migración del ingestador (`ingestor/alembic/versions/*_web_readonly_role.py`): `LOGIN`, sin atributos de administración, `USAGE` en `gold`, `SELECT` en sus vistas y privilegios por defecto para vistas futuras. No tiene acceso a `silver`/`bronze` ni escritura/`CREATE` en `gold`.
- La migración **no fija contraseña**. En local, una vez:

  ```bash
  docker compose exec db psql -U votoscope -d votoscope \
    -c "ALTER ROLE votoscope_web PASSWORD 'votoscope_web'"
  ```

  En producción la contraseña se configura en el panel del proveedor y se pasa como secreto (`DATABASE_URL`) al runtime de Vercel.

## Reglas

- **Solo lectura**: la web nunca escribe ni migra la base de datos; de eso se encarga el ingestador.
- **BFF obligatorio**: toda llamada a PostgreSQL o a servicios externos vive bajo `web/app/api/`; las páginas, componentes y `lib/` no importan `pg` ni contienen SQL. El navegador solo puede llamar a los Route Handlers `/api/*` (nunca a la base). Nada de Server Actions que sirvan datos.
- Los Route Handlers validan la entrada, responden `Cache-Control: no-store` y traducen cualquier fallo a `500 { error: "internal" }` sin filtrar SQL, credenciales ni stack.
- Consultar las vistas `gold.*`, no las tablas `silver` directamente. Si falta un dato para una pantalla, se añade la vista en el ingestador (ERD ↔ modelos ↔ migración). Contrato de datos: [`../docs/db/gold.md`](../docs/db/gold.md).
- Las credenciales de Postgres nunca llegan al cliente: los datos se leen en servidor.
- **Dependencias**: pnpm y la lista aprobada en [`../specs/016_web_scaffold/design.md`](../specs/016_web_scaffold/design.md). Ninguna nueva sin consentimiento explícito del usuario (ver [`../.agents/conventions.md`](../.agents/conventions.md)).

## Logging

- `lib/logging.ts`, sin dependencias: `LogLevel`, `parseLogLevel`, `createLogger(sink?)` y `logger`.
- Niveles `debug`/`info`/`warn`/`error`; `debug`/`info` → `console.log`, `warn` → `console.warn`, `error` → `console.error`.
- El nivel efectivo se calcula en cada llamada desde `LOG_LEVEL`; si falta o no es válido, `info`. Formato: fecha ISO, nivel y ámbito `[votoscope-web]`.
- Nunca se loguean la URL de conexión ni credenciales.

## Tests

- Runner nativo de Node: `node --test` (sin framework ni transpilador; Node ≥ 24). Los tests viven en `web/tests/*.test.ts`.
- Imports relativos **con extensión explícita** (`.ts`); `tsconfig.json` tiene `allowImportingTsExtensions`.
- Herméticos (sin base): `structure.test.ts`, `bff.test.ts`, `gold_contract.test.ts`, `logging.test.ts`, `docs.test.ts`.
- Live (se saltan sin `DATABASE_URL`, base o datos): `gold_live.test.ts` ejecuta el servicio real contra `gold`.
- `pnpm test` carga `.env.local` si existe (`--env-file-if-exists`). El render de `.tsx` no se testea con el runner nativo: se verifica con el smoke de `pnpm dev`.
