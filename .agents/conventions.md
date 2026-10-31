# Convenciones

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md). El estilo de código está en [`style.md`](style.md).

## Base de datos

- Tablas y columnas en **inglés**, con el vocabulario del dominio (election, polling_station, census…). ERD, modelos y migración siguen el modelo v2.
- PK: código natural cuando es único y estable (`autonomous_community.ine_code`, `province.ine_code`); en el resto, PK sustituta `id` entero autoincremental, con los códigos naturales aparte con `UNIQUE` (`ine_code`, `slug`, `(election_id, code)`, `(polling_station_id, election_id)`…). No se usan `uuid`.
- Claves ajenas: `<tabla>_<clave referenciada>` (`autonomous_community_ine_code`, `province_ine_code`; `polling_station_id`, `election_id`…).
- Agregados y porcentajes solo en `gold`; `silver` guarda hechos.
- `data/raw/` es inmutable y no se versiona.

## Idioma

- Identificadores de código: inglés.
- Documentación de trabajo (este directorio y los AGENTS.md): español.

## Logging

- Ambas partes (ingestador y web) registran logs con niveles estándar: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- El nivel se fija por variable de entorno: **`LOG_LEVEL`** (por defecto `INFO`). Nunca hardcodeado.
- Ingestador: biblioteca estándar (`logging`), sin dependencias extra; un único `configure_logging()` que arranca cada entrypoint; formato único (fecha · nivel · logger · mensaje); loggers por módulo (`getLogger(__name__)`).
- Web: `web/lib/logging.ts`, sin dependencias; niveles `debug`/`info`/`warn`/`error` sobre `console` (`debug`/`info` → `log`, `warn` → `warn`, `error` → `error`), formato con fecha ISO, nivel y ámbito. El nivel efectivo se calcula en cada llamada desde `LOG_LEVEL`; si falta o no es válido, `info`. No hay `NEXT_PUBLIC_LOG_LEVEL`.
- Nunca se loguean secretos ni la URL de conexión.

## Dependencias

- **Ninguna dependencia nueva se añade sin consentimiento explícito del usuario**: primero se propone (problema que resuelve, por qué no basta la stdlib o lo ya instalado) y se espera respuesta.
- Solo si aporta de verdad y es utilizable (mantenida, compatible, sin duplicar lo existente).
- Instalación con el gestor del proyecto: `uv add` en el ingestador y `pnpm add` en la web.
- Ya aprobadas (ingestador): SQLAlchemy, Alembic, psycopg, pydantic-settings.
- Ya aprobadas (web): las del template de Next.js (`next`, `react`, `react-dom`, TypeScript, ESLint, Tailwind), `pg` + `@types/pg` y la base de shadcn/ui (`class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `@radix-ui/react-slot` y las primitivas que añada cada componente). No hay framework de tests.

## Tests

- **TDD** para la lógica (parsers, loader, transformaciones): primero el test que falla, luego el código mínimo, luego refactor.
- Framework: **pytest** (dev-dependency aprobada); los tests del ingestador viven en `ingestor/tests/`.
- Fixtures de los parsers: `ingestor/tests/fixtures/` (recortes reales mínimos + casos sintéticos); los tests no dependen de `refs/` ni de la red.
- CI: al montar el loader — GitHub Actions (`uv sync` + ruff + pytest + `alembic check` con Postgres de servicio).
- Web: runner nativo `node --test` (Node ≥ 24, sin framework ni transpilador); los tests viven en `web/tests/*.test.ts` y los imports relativos llevan extensión `.ts`. Herméticos (estructura/BFF, contrato del SQL, logging, docs) y live (`gold_live.test.ts`, se salta sin `DATABASE_URL` o sin base). `pnpm test` los ejecuta; `init.sh` añade `pnpm test` y `pnpm lint` cuando existe `web/node_modules`.

## Frontend

- **BFF obligatorio**: toda consulta a PostgreSQL o a servicios externos vive en `web/app/api/` (Route Handlers y módulos privados `_lib/`). Nada de SQL ni de `pg` en páginas, componentes o `lib/`, ni Server Actions que sirvan datos. El navegador solo llama a `/api/*`; las credenciales nunca salen del servidor.
- El SQL de `gold.*` vive únicamente en `web/app/api/_lib/gold.ts`; las vistas y columnas son las del contrato [`../docs/db/gold.md`](../docs/db/gold.md), sin redefinirlas ni agregar hechos en la web.
