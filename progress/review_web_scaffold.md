# Review — feature 16 `web_scaffold`

**Veredicto:** APPROVED

Rama `feature/web-scaffold` (apilada sobre `feature/delivery-gold`), cambios en el working tree y sin commits. Revisión independiente con `./init.sh` re-ejecutado, build sin base, smoke real de `pnpm dev`, introspección del rol en Postgres y mutaciones temporales de los tests estructurales. Fuera de alcance por decisión del usuario: `specs/018_source_norm/` y el estado `spec_ready` de la 18 en `feature_list.json`.

## Verificación independiente

- `./init.sh`: **exit 0** — arnés y specs, `uv sync`, `ruff check`, `ruff format`, **231 pytest** (incluidos los 7 de `test_web_role.py`, sin skips) y **24 tests de `node --test`** (`0 skipped`), `pnpm lint`, y `alembic check` sin drift.
- `pnpm install --frozen-lockfile`: exit 0 (lockfile reproducible).
- Build sin base: `DATABASE_URL=postgresql://nope:nope@127.0.0.1:1/nope pnpm build` compila y deja `/`, `/api/gold/latest-election` y `/api/gold/national-results` como `ƒ (Dynamic)`; no intenta consultar la base.
- Smoke real con `.env.local` y `next dev -p 3117`: portada **200** con `<h1 …>congress</h1>`, `GET /api/gold/latest-election` **200** con `cache-control: no-store`, y `GET /api/gold/national-results?electionId=0` **400** `{"error":"invalid_election_id"}`.
- Rol en el Postgres local: `votoscope_web` con `rolcanlogin=true`, `rolsuper=false`, `rolcreatedb=false`, `rolcreaterole=false`; `USAGE` en `gold` y sin `CREATE`; sin `USAGE` en `silver`/`bronze`; las 6 vistas con `SELECT`; un `SELECT` por defecto en `pg_default_acl` para vistas futuras; `alembic current` en `9f3c2a1b7d40 (head)`.
- Mutaciones temporales de los tests estructurales (copias fuera del working tree, originales restaurados): añadir SQL a `app/page.tsx`, importar `pg` desde `lib/logging.ts`, añadir `"use server"` a la portada, crear un tercer `route.ts`, quitar `force-dynamic`, romper `no-store`, aceptar `electionId=0`, cambiar el SQL a `silver` o cambiar `level='national'` por `'community'` **hacen fallar** `structure.test.ts`, `bff.test.ts` o `gold_contract.test.ts`, según el caso. La regla del BFF no tiene un test vacuo.
- `git status --short` sin cambios no previstos; `web/.env.local` ignorado por `web/.gitignore:34` y no trackeado; no hay credenciales reales en ficheros versionables (`web/.env.example` y el README solo llevan la credencial de desarrollo aprobada en `design.md` §D7).

## Trazabilidad requirements ↔ tests

- R1: [x] `web/tests/structure.test.ts:35-79` (scripts `dev`/`build`/`start`/`lint`/`test`, `pnpm@10.28`, `engines >=24`, dependencias, `pnpm-lock.yaml`, sin `package-lock.json`); `pnpm build` verificado sin base.
- R2: [x] `web/tests/gold_contract.test.ts:52-72` (solo `SELECT`, solo `gold.*`, vistas del contrato, `ORDER BY election_date DESC LIMIT 1`, `$1` y `level = 'national'`) + `web/tests/structure.test.ts:102-122` (SQL y `pg` solo bajo `app/api/`) + `web/tests/gold_live.test.ts:27-96` (servicio real contra `gold`).
- R3: [x] `web/tests/structure.test.ts:124-138` (portada importa `@/app/api/_lib/gold.ts`, no es cliente y declara `force-dynamic`) + `web/tests/gold_live.test.ts:27-96` (última elección = `max(election_date)`, resultados nacionales) + smoke de `pnpm dev` (portada 200 con el `<h1>` de la elección).
- R4: [x] `web/tests/structure.test.ts:102-122` (sin SQL/`pg`/`use server`/`NEXT_PUBLIC_DATABASE_URL` fuera de `app/api/`) + `web/tests/bff.test.ts:31-49` (GET, `force-dynamic`, `no-store`, sin SQL ni `pg` en las rutas) + `web/tests/bff.test.ts:52-61` (400 sin tocar la base). El enmascarado del 500 (`{"error":"internal"}` + `no-store`) se verificó manualmente con una `DATABASE_URL` inalcanzable; ver observación 2.
- R5: [x] `ingestor/tests/test_web_role.py:74-79` (la migración contiene `CREATE ROLE … LOGIN` y `DROP ROLE`) y `:85-97` (atributos reales del rol); migración `ingestor/alembic/versions/9f3c2a1b7d40_web_readonly_role.py:22-28`.
- R6: [x] `ingestor/tests/test_web_role.py:100-114` (`USAGE` de `gold` y `SELECT` en todas las vistas).
- R7: [x] `ingestor/tests/test_web_role.py:117-132` (`pg_default_acl` con `SELECT` para `votoscope_web`).
- R8: [x] `ingestor/tests/test_web_role.py:135-169` (sin acceso a `silver`/`bronze`, sin `CREATE` ni escritura en `gold`).
- R9: [x] `ingestor/tests/test_web_role.py:66-71` (la migración no contiene `PASSWORD` ni URLs) + `web/tests/docs.test.ts:17-32` (`ALTER ROLE` documentado en `web/AGENTS.md`).
- R10: [x] `web/tests/logging.test.ts:32-61` (formato ISO, nivel, ámbito; `debug`/`info` → `log`, `warn` → `warn`, `error` → `error`).
- R11: [x] `web/tests/logging.test.ts:64-90` (filtrado por `LOG_LEVEL=warn` y `error`).
- R12: [x] `web/tests/logging.test.ts:93-109` (`undefined`, vacío y valor desconocido → `info`; mayúsculas aceptadas).
- R13: [x] `web/tests/gold_live.test.ts:99-131` (con `LOG_LEVEL=debug` y `console` capturada, la consulta real no filtra la URL ni la contraseña).
- R14: [x] `web/tests/structure.test.ts:140-148` (`.env.example` con el rol de solo lectura y sin `NEXT_PUBLIC_`); grep confirma que `process.env.DATABASE_URL` solo se lee en `web/app/api/_lib/db.ts` y en tests.
- R15: [x] `web/tests/docs.test.ts:17-32` (`votoscope_web`, `app/api/`, `pnpm test`, `node --test`, `LOG_LEVEL`, `ALTER ROLE`, `docs/db/gold.md`).
- R16: [x] `web/tests/docs.test.ts:35-43` (`node --test`, `web/tests`, `pnpm`, `app/api/`, `LOG_LEVEL`, sin «se decidirá en su scaffold») + sección web de `init.sh:117-136`.
- R17: [x] `web/tests/docs.test.ts:46-58` (sin «Pendiente de scaffold» y con comandos web/`votoscope_web` en `.agents/architecture.md` y `.agents/environment.md`).
- R18: [x] `web/tests/structure.test.ts:150-165` (`components.json`, `components/ui/`, `cn`, tokens Tailwind) + `:124-138` (import de `@/components/ui/`) + portada renderizada en el smoke.
- R19: [x] `web/tests/docs.test.ts:61-78` (requisitos Node/pnpm, `pnpm dev`, `.env.local`, `votoscope_web`, `app/api/`, `shadcn`, `docs/db/gold.md`).

## Tasks completas

- T1–T17: [x] — `specs/016_web_scaffold/tasks.md:9-25`, todas marcadas y sin `[ ]`. T17 tiene evidencia de tests, build, smoke, downgrade/upgrade del rol y `init.sh` en `progress/impl_web_scaffold.md`; las comprobaciones de esta review reproducen las principales.

## Checkpoints

- C1: [x] — piezas base y los 4 agentes presentes (`init.sh` §2); `./init.sh` exit 0.
- C2: [x] — una sola feature `in_progress` (16); 17 ya estaba `spec_ready` en `HEAD` y 18 es el estado movido por el usuario, fuera de alcance; features `done` con tests verdes; `progress/current.md` describe la sesión activa.
- C3: [x] — sin cambios de modelo (el rol no toca ERD ni `models.py`, como fija `design.md`); sin DDL a mano ni migraciones editadas; `alembic check` sin drift; capas y BFF respetados; logging por niveles; sin `print()` ni TODOs. Observación de dependencias en el punto 4.
- C4: [x] en local — pytest 231/231, `ruff check`, `ruff format --check`, `alembic check`, `pnpm test` 24/24 y `pnpm lint` verdes. Sub-item CI: [ ] no hay run de `ingestor.yml` para la rama porque no se ha pusheado (por diseño del flujo); el equivalente local está verde.
- C5: [ ] — pendiente del cierre post-OK: commits atómicos, entrada en `progress/history.md` y paso de la feature a `done`. El working tree no tiene basura de la feature; `.next`, `next-env.d.ts`, `node_modules` y `.env.local` están ignorados; no hay commits ni push, correcto en esta fase.
- C6: [x] — `specs/016_web_scaffold/` con `requirements.md`, `design.md` y `tasks.md`; requirements EARS (R2/R4 agrupan varias cláusulas, pero son verificables y vienen del spec aprobado); T1–T17 `[x]`; R1–R19 cubiertos. Nota: los R de la web se verifican en `web/tests/` según `design.md` §D8 y los de base de datos en `ingestor/tests/`; no hay R sin test.

## Observaciones no bloqueantes (priorizadas)

1. **`web/tests/gold_live.test.ts:10-24` — skip demasiado amplio.** `UNAVAILABLE` incluye `does not exist` y `connect`; un fallo real de esquema (por ejemplo, una columna mal escrita en `gold.ts`) se convierte en `t.skip` y el suite queda verde. Conviene limitar el skip a errores de conexión/`DATABASE_URL` ausente y comprobar la existencia de la vista con `to_regclass`, dejando que un error de columna falle. No afecta al estado actual (los live se ejecutaron sin skips en local), pero debilita R2/R3/R13 en un entorno a medias.
2. **`web/tests/bff.test.ts:31-61` — falta cubrir el camino de éxito y el 500.** El test verifica el 400 y el texto de las rutas, pero no invoca `GET` con un `electionId` válido ni provoca un fallo para comprobar `{"error":"internal"}` sin detalle. El comportamiento es correcto (verificado a mano con una `DATABASE_URL` inalcanzable: 500, `no-store`, cuerpo enmascarado), pero no queda automatizado; un test con un servicio/`queryRows` inyectable o un subproceso con URL inválida cerraría R4.
3. **`web/tests/structure.test.ts:32-33,102-122` — dos evasiones posibles.** `PG_IMPORT` no detecta `await import("pg")`, y un componente `"use client"` que importe `@/app/api/_lib/gold.ts` no contiene SQL ni `pg` directo: el escaneo no lo vería y el servicio BFF acabaría en el bundle cliente. Además el escaneo solo mira `.ts`/`.tsx` bajo `app` (fuera de `app/api`), `components` y `lib`; un `.js`/`.mjs` en `lib` se escaparía. Son huecos de futuro, no del código actual; conviene prohibir imports de `app/api/_lib` en ficheros con `"use client"` y ampliar el escaneo.
4. **`web/package.json:25` + `web/next.config.ts:8-14` — `@tailwindcss/turbopack` en vez de `@tailwindcss/postcss`.** `design.md:43` aprobaba el segundo; la plantilla de esta versión de Next usa el primero. Está documentado en `progress/impl_web_scaffold.md` (desviación 4), el build funciona y el test acepta cualquiera de los dos (`web/tests/structure.test.ts:68-72`), pero si el gate de dependencias se lee literal, hay que añadir `@tailwindcss/turbopack` a la lista aprobada o volver al pipeline del diseño. No es un defecto funcional.
5. **`web/app/api/_lib/gold.ts:77-79` — `electionDate` se serializa como `Date` local.** En el smoke, `GET /api/gold/latest-election` devuelve `"electionDate":"2023-07-22T22:00:00.000Z"` para la elección del 23 de julio (huso local UTC+2). La portada formatea en servidor y muestra el 23 correctamente; un consumidor del JSON en UTC podría ver el 22. Para el contrato HTTP sería más seguro emitir `YYYY-MM-DD` (o normalizar a UTC). No afecta a R3 tal como está redactado.
6. **`.agents/conventions.md:20-23` — matiz de niveles.** La primera viñeta dice que ambas partes usan `DEBUG/INFO/WARNING/ERROR/CRITICAL`; la web no tiene `critical` y usa `debug/info/warn/error`. La viñeta siguiente lo aclara, pero se puede unificar para que la constitución no se contradiga. Cosmético.

## Cambios requeridos

Ninguno. La implementación cumple R1–R19, todas las tasks están `[x]`, el arnés está verde y las observaciones anteriores son deuda de endurecimiento de tests o de documentación, no bloqueos de la feature.
