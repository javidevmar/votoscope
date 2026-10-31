# Votoscope — web

Frontend del agregador de resultados electorales de España. Next.js (App Router, TypeScript) que lee las vistas `gold` en servidor a través de un BFF en `app/api/`. El contrato de datos está en [`../docs/db/gold.md`](../docs/db/gold.md) y las reglas para agentes en [`AGENTS.md`](AGENTS.md).

## Requisitos

- Node **≥ 24** (el runner de tests usa el *type stripping* nativo de TypeScript).
- pnpm **10.28** (el `packageManager` del `package.json` lo fija con Corepack: `corepack enable`).
- El Postgres local del repo (`docker compose up -d --wait`) con las migraciones aplicadas (`cd ingestor && uv run alembic upgrade head`).

## Instalación y entorno

```bash
cd web
pnpm install
cp .env.example .env.local
```

`.env.local` (gitignored) necesita:

- `DATABASE_URL` con el rol de solo lectura `votoscope_web`, por defecto `postgresql://votoscope_web:votoscope_web@localhost:5434/votoscope`.
- `LOG_LEVEL` (`debug`/`info`/`warn`/`error`; por defecto `info`).

La contraseña del rol no está en la migración: se fija por entorno. En local, una vez:

```bash
docker compose exec db psql -U votoscope -d votoscope \
  -c "ALTER ROLE votoscope_web PASSWORD 'votoscope_web'"
```

## Comandos

| Comando | Qué hace |
| --- | --- |
| `pnpm dev` | servidor de desarrollo en <http://localhost:3000> |
| `pnpm build` | build de producción (no necesita base: la portada es `force-dynamic`) |
| `pnpm start` | sirve el build |
| `pnpm lint` | ESLint (`eslint-config-next`) |
| `pnpm test` | tests con `node --test` (carga `.env.local` si existe) |

## Estructura

```
app/
├── api/            # BFF: única frontera de datos
│   ├── _lib/       # db.ts, gold.ts (SQL de gold.*), params.ts
│   └── gold/       # Route Handlers latest-election y national-results
├── layout.tsx · page.tsx · globals.css
components/ui/      # shadcn/ui (button, card, …)
lib/                # logging.ts y utils.ts
tests/              # *.test.ts con node --test
```

- **BFF**: toda consulta a PostgreSQL o a servicios externos vive en `app/api/`; las páginas y componentes no importan `pg` ni contienen SQL. La portada (Server Component) importa el servicio `app/api/_lib/gold.ts` y lo ejecuta en servidor; el navegador solo puede llamar a `/api/*`.
- **Rol `votoscope_web`**: solo lectura sobre `gold` (sin acceso a `silver`/`bronze`), creado por la migración del ingestador.
- **UI**: Tailwind CSS 4 + shadcn/ui (`components.json`, tokens en `app/globals.css`). Para añadir componentes: `pnpm dlx shadcn@latest add <componente>`.

## Tests

- Herméticos (sin base): estructura y frontera del BFF, contrato del SQL, logging y documentación.
- Live: `tests/gold_live.test.ts` consulta la base local; se salta sin `DATABASE_URL` o si Postgres no responde.
- El render de la portada se comprueba con `pnpm dev` (el runner nativo no transforma `.tsx`).
