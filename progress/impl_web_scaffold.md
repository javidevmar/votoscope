# Implementación — `web_scaffold` (feature 16)

- **Rama:** `feature/web-scaffold` (apilada sobre `feature/delivery-gold`), cambios en el working tree, sin commits.
- **Estado:** implementación completa; T1–T17 `[x]` en [`../specs/016_web_scaffold/tasks.md`](../specs/016_web_scaffold/tasks.md). Pendiente: revisión del `reviewer` y OK del usuario.
- **Verificación:** `./init.sh` en verde (231 tests de pytest + 24 de `node --test` + lint + `alembic check` sin drift).

## Qué se ha hecho

- **Scaffold** (`web/`): Next.js 16.4.3 (App Router, TS, Turbopack), pnpm 10.28, Tailwind 4 y shadcn/ui; `pg` + `@types/pg`; scripts `dev`/`build`/`start`/`lint`/`test`.
- **Logging** (`web/lib/logging.ts`): niveles, `LOG_LEVEL` con fallback a `info`, formato ISO + nivel + `[votoscope-web]`, sink inyectable, sin dependencias.
- **BFF** (`web/app/api/`): `_lib/db.ts` (Pool perezoso, `queryRows`, logging sin credenciales), `_lib/gold.ts` (único SQL, `SELECT` a `gold.*`, mapeo `bigint`/`numeric` → `number`), `_lib/params.ts` (`parseElectionId`), Route Handlers `latest-election` y `national-results` (`no-store`, 400 de validación, 500 `{ error: "internal" }`).
- **Portada** (`app/page.tsx`): Server Component `async` con `force-dynamic`, servicio del BFF en servidor, `Card`/`Button` de shadcn, fallbacks de `turnout_pct`/`party_color` y estado vacío. `app/layout.tsx` con `lang="es"`.
- **Rol de solo lectura**: migración `ingestor/alembic/versions/9f3c2a1b7d40_web_readonly_role.py` (`down_revision = bcd8a7409aec`), `USAGE` + `SELECT` en `gold`, `ALTER DEFAULT PRIVILEGES`, sin contraseña; `ingestor/tests/test_web_role.py`.
- **Entorno**: `web/.env.example` (rol `votoscope_web`, `LOG_LEVEL=INFO`), `web/.env.local` local (gitignored) con la contraseña de desarrollo fijada con `ALTER ROLE`.
- **Docs**: `web/AGENTS.md` reescrito, `web/README.md` nuevo, `.agents/conventions.md`, `.agents/architecture.md`, `.agents/environment.md` y `.agents/style.md` actualizados.
- **Arnés**: sección web en `init.sh` (`pnpm test` + `pnpm lint` si hay `node_modules`).

## Orden de ejecución (desviación prevista)

Se aplicó **T12 → T13 antes de T11**: el test live de la web usa el rol `votoscope_web`, que crea la migración. El test del rol se escribió antes de la migración (rojo por ausencia del fichero) y la migración se aplicó antes de `gold_live.test.ts`. Sin otras alteraciones de orden.

## Desviaciones y arreglos respecto al spec

1. **Artefactos del scaffold interrumpido (T1)**: `components/ui/card.tsx` importaba `cn` de `"cn"` y `button.tsx` usaba `Slot.Root` (inexistente en `@radix-ui/react-slot`). Corregidos a `@/lib/utils` y `Slot`; sin ellos `pnpm build` no compilaba.
2. **Next 16.4.3 genera con Cache Components activado**: `cacheComponents: true` es incompatible con `export const dynamic = "force-dynamic"` (error de build), que el spec exige en la portada y en los Route Handlers (D9/D4). Se eliminaron `cacheComponents`/`partialPrefetching` de `next.config.ts`; las rutas salen como `ƒ (Dynamic)` en el build.
3. **`next dev` añadía un bloque de reglas a `web/AGENTS.md`**: se desactivó con `agentRules: false` en `next.config.ts` y se retiró el bloque generado, para que la constitución no se modifique sola.
4. **Pipeline CSS del template**: esta versión de `create-next-app` usa `@tailwindcss/turbopack` + regla `turbopack` en `next.config.ts` en vez de `@tailwindcss/postcss` + `postcss.config.mjs` (variación de versión permitida por D1). El test estructural acepta cualquiera de los dos; el estado exigido por R18 (tokens, `components.json`, `cn`) está cubierto.
5. **`init.sh`**: `pnpm test --silent` pasa `--silent` a `node --test` y falla; se usa `pnpm --silent test` / `pnpm --silent lint` (forma correcta en pnpm).
6. **`web/.gitignore`**: se añadió `!.env.example` para que el ejemplo se versione pese a `.env*` (el `.gitignore` raíz no puede des-ignorar dentro de un subdirectorio).
7. **`"type": "module"` en `web/package.json`**: elimina el warning `MODULE_TYPELESS_PACKAGE_JSON` de `node --test`; no cambia el comportamiento (los tests ya se detectaban como ESM).
8. **Formato de fecha en el test live**: `pg` devuelve `date` como `Date` local; la comparación con `max(election_date)` se hace con la fecha local (`getFullYear`/`getMonth`/`getDate`), no con `toISOString()` (que desplaza el día en husos al este de UTC).

## Trazabilidad R ↔ test

| R | Test(s) |
| --- | --- |
| R1 | `web/tests/structure.test.ts` → «package.json: scripts, package manager and approved dependencies» y «App Router: layout, page and the two BFF routes exist»; `pnpm build` (smoke) |
| R2 | `web/tests/gold_contract.test.ts` (3 tests); `web/tests/bff.test.ts` → «parseElectionId…» y «each Route Handler…»; `web/tests/gold_live.test.ts` → «latest election matches max(election_date)…»; `web/tests/structure.test.ts` → «BFF boundary…» |
| R3 | `web/tests/structure.test.ts` → «page: Server Component…»; `web/tests/gold_live.test.ts` → «latest election…»; smoke de `pnpm dev` (portada 200 con `<h1>congress</h1>`) |
| R4 | `web/tests/structure.test.ts` → «BFF boundary…» y «page: Server Component…»; `web/tests/bff.test.ts` → «each Route Handler…» y «national-results returns 400…» |
| R5 | `ingestor/tests/test_web_role.py` → `test_role_is_login_without_admin_attributes`, `test_migration_creates_and_drops_the_role` |
| R6 | `ingestor/tests/test_web_role.py` → `test_role_has_usage_and_select_on_every_gold_view` |
| R7 | `ingestor/tests/test_web_role.py` → `test_default_privileges_grant_select_on_future_gold_relations` |
| R8 | `ingestor/tests/test_web_role.py` → `test_role_cannot_read_silver_or_bronze`, `test_role_cannot_write_or_create_in_gold` |
| R9 | `ingestor/tests/test_web_role.py` → `test_migration_source_has_no_credentials`; `web/tests/docs.test.ts` → «web/AGENTS.md documents…» (`ALTER ROLE`) |
| R10 | `web/tests/logging.test.ts` → «format: ISO timestamp…», «channels: debug/info…» |
| R11 | `web/tests/logging.test.ts` → «filtering: LOG_LEVEL=warn…», «filtering: LOG_LEVEL=error…» |
| R12 | `web/tests/logging.test.ts` → «fallback: undefined and unknown…», «fallback: without LOG_LEVEL…» |
| R13 | `web/tests/gold_live.test.ts` → «debug logs never contain the connection URL or password» |
| R14 | `web/tests/structure.test.ts` → «environment: .env.example…» y «BFF boundary…» (sin `NEXT_PUBLIC_DATABASE_URL`) |
| R15 | `web/tests/docs.test.ts` → «web/AGENTS.md documents the scaffold, BFF, role, logging and tests» |
| R16 | `web/tests/docs.test.ts` → «.agents/conventions.md includes the web strategy»; sección web de `init.sh` |
| R17 | `web/tests/docs.test.ts` → «architecture and environment no longer call the web pending» |
| R18 | `web/tests/structure.test.ts` → «UI system: shadcn and Tailwind tokens are configured» y «page: Server Component…» (import de `@/components/ui/`) |
| R19 | `web/tests/docs.test.ts` → «web/README.md is the quickstart guide» |

## Evidencias de verificación (2026-10-29, local)

### Tests, lint y build

```text
$ cd web && pnpm test
ℹ tests 24 · pass 24 · fail 0 · skipped 0

$ cd web && pnpm lint
(exit 0, sin avisos)

$ cd web && pnpm build
✓ Compiled successfully
Route (app)
┌ ƒ /                                  (force-dynamic)
├ ○ /_not-found
├ ƒ /api/gold/latest-election
└ ƒ /api/gold/national-results
```

### Smoke de `pnpm dev` (Postgres local, `.env.local`, rol `votoscope_web`)

```text
$ cd web && pnpm dev     # http://localhost:3000
$ curl -s -o /tmp/web_home.html -w '%{http_code}' http://localhost:3000/
200
$ grep '<h1' /tmp/web_home.html
<h1 class="text-3xl font-semibold tracking-tight">congress</h1>

$ curl -s -D - http://localhost:3000/api/gold/latest-election
HTTP/1.1 200 OK
cache-control: no-store
content-type: application/json
{"election":{"electionId":1,"electionType":"congress","electionDate":"2023-07-22T22:00:00.000Z","electionName":null,"census":37469141,"nullVotes":264382,"blankVotes":200682,"candidatureVotes":24487589,"validVotes":24688271,"voters":24952653,"turnoutPct":66.6}}

$ curl -s -w ' status=%{http_code}' 'http://localhost:3000/api/gold/national-results?electionId=0'
{"error":"invalid_election_id"} status=400
```

### Rol de solo lectura

```text
$ cd ingestor && uv run alembic downgrade -1
INFO  Running downgrade 9f3c2a1b7d40 -> bcd8a7409aec, web read-only role
$ psql -tAc "select count(*) from pg_roles where rolname='votoscope_web'"
0
$ uv run alembic upgrade head
INFO  Running upgrade bcd8a7409aec -> 9f3c2a1b7d40, web read-only role
$ psql -c "ALTER ROLE votoscope_web PASSWORD 'votoscope_web'"
ALTER ROLE
$ uv run alembic check
No new upgrade operations detected.
$ uv run pytest tests/test_web_role.py -q
7 passed
```

### Arnés completo

```text
$ ./init.sh
[OK] pytest: todos los tests pasan            (231 passed)
[OK] pnpm test: tests de la web pasan         (24 passed)
[OK] pnpm lint
[OK] alembic check: sin drift
[OK] Entorno listo. Puedes empezar a trabajar.
```

## Limitaciones conocidas

- El render de `.tsx` no se prueba con `node --test` (el *type stripping* no transforma JSX); se cubre con el smoke de `pnpm dev`, como fija el spec (D8).
- Los tests live de `gold_live.test.ts` y de `test_web_role.py` se saltan sin `DATABASE_URL`/Postgres/rol, respectivamente.
- `pnpm build` necesita red para la fuente Geist de `next/font/google`; en su defecto, Next usa la fuente de respaldo.
