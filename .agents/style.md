# Estilo

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). Nombres y convenciones: [`conventions.md`](conventions.md).

## Python (ingestor)

- Dependencias y ejecución siempre con **uv** (nunca pip directo).
- Type hints en todo el código; SQLAlchemy 2 con `Mapped[...]`.
- Docstrings y comentarios: inglés, concisos.
- Lint/format: **ruff** con configuración por defecto (se añade al arrancar el loader).

## Commits

- Conventional commits, en inglés (`chore:`, `feat:`, `fix:`…).
- Commits atómicos: un propósito por commit.
- **Cuándo**: el commiteo atómico es el paso final, tras implementar y revisar, y solo con el OK explícito del usuario.

## Ramas, PRs e iniciativas

- Ramas por feature desde `main`: `feature/<nombre>`. Nunca se trabaja directo en `main`.
- **Iniciativa = stack de PRs**: las features de una misma iniciativa lo declaran en el campo `"initiative"` de [`feature_list.json`](../feature_list.json) y se agrupan en una rama y un PR por feature (el trabajo se divide).
- Ramas del stack: la primera feature vive en `feature/<slug>` y las siguientes se apilan encima: `feature/<slug>-<sufijo>`, creadas desde la rama de la feature anterior.
- PRs: `gh pr create --base <rama-padre>` (`main` solo para la base del stack). GitHub agrupa el stack y re-apunta los hijos al mergear.
- Features sueltas: `feature/<nombre>` desde `main` y PR a `main`.
- El push también requiere OK explícito del usuario.

## Frontend

- TypeScript estricto; App Router con Server Components por defecto (componentes cliente solo si hacen falta).
- Dependencias y ejecución con **pnpm** (`pnpm add`, `pnpm dlx shadcn@latest add …`).
- Lint: **ESLint** con `eslint-config-next` (`pnpm lint`). Tests: `node --test` (`pnpm test`).
- SQL solo en `web/app/api/_lib/gold.ts`; nada de SQL ni de `pg` en páginas, componentes o `lib/`.
