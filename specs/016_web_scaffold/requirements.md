# Requisitos — `web_scaffold`

Feature `id 16` de [`feature_list.json`](../../feature_list.json). Alcance: el scaffold de la web (`web/`: aplicación Next.js con App Router que lee las vistas `gold` en servidor), el rol de Postgres de solo lectura creado por migración y el logging por niveles con `LOG_LEVEL` en servidor. La documentación afectada (`web/AGENTS.md`, [`.agents/conventions.md`](../../.agents/conventions.md), [`.agents/architecture.md`](../../.agents/architecture.md), [`.agents/environment.md`](../../.agents/environment.md)) se actualiza en la misma feature, porque el acceptance lo exige o porque quedaría obsoleta.

Depende de las features 12–15 (van antes en la cola): el contrato `gold` ↔ front de [`specs/015_delivery_gold/`](../015_delivery_gold/design.md) y su documento [`docs/db/gold.md`](../../docs/db/gold.md) están cerrados y **no se redefinen aquí**: la web cita las vistas y columnas tal cual (`election_summary`, `result_by_area`, `result_by_station`, `station_turnout`, `poll_flat`, `poll_trend`). Tampoco se toca el ingestador salvo la migración del rol y sus tests.

## R1

El sistema DEBE incluir en `web/` una aplicación Next.js con App Router y TypeScript, gestionada con pnpm (`web/package.json` + `web/pnpm-lock.yaml`), con los scripts `dev`, `build`, `start`, `lint` y `test`.

## R2

El sistema DEBE concentrar las consultas a las vistas `gold` en `web/app/api/_lib/gold.ts`, como únicas sentencias SQL de la aplicación, todas de solo lectura (`SELECT`) y dirigidas exclusivamente al esquema `gold`; ningún otro módulo (páginas, componentes, `lib/`) contiene SQL ni importa `pg`.

## R3

CUANDO se sirve la página de inicio, el sistema DEBE leer en un Server Component, a través del servicio del BFF, la elección más reciente de `gold.election_summary` (la de `election_date` máxima) y sus resultados nacionales de `gold.result_by_area` (`level = 'national'`), y mostrar sus valores.

## R4

El sistema DEBE exponer los datos de `gold` solo a través del BFF: los Route Handlers de `web/app/api/` son la única superficie HTTP de datos y toda llamada a PostgreSQL o a servicios externos vive bajo `web/app/api/`. El navegador no DEBE recibir consultas SQL, credenciales ni acceso directo a la base; las páginas y componentes no DEBEN importar `pg` ni contener SQL, y no DEBE haber Server Actions que sirvan datos.

## R5

CUANDO se aplica la migración del rol con `uv run alembic upgrade head`, el sistema DEBE crear el rol `votoscope_web` con `LOGIN` y sin atributos de administración (`NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`).

## R6

El sistema DEBE conceder al rol `votoscope_web` `USAGE` sobre el esquema `gold` y `SELECT` sobre todas las vistas existentes de `gold`.

## R7

El sistema DEBE declarar privilegios por defecto (`ALTER DEFAULT PRIVILEGES`) para que las vistas creadas en `gold` en el futuro sean legibles por `votoscope_web` sin una migración de privilegios adicional.

## R8

El sistema NO DEBE conceder a `votoscope_web` acceso a `silver` ni `bronze` (`USAGE` ni `SELECT`) ni permisos de escritura o de creación en `gold` (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `CREATE`).

## R9

La migración del rol NO DEBE fijar la contraseña de `votoscope_web`: cada entorno la configura fuera de git (`ALTER ROLE … PASSWORD` en local, documentado; panel del proveedor en producción).

## R10

El sistema DEBE registrar los logs de la web en el servidor con los niveles `debug`, `info`, `warn` y `error` y formato propio sobre `console`, sin dependencias nuevas.

## R11

CUANDO se emite un mensaje de log en el servidor, el sistema DEBE escribirlo solo si su nivel es igual o superior al nivel efectivo de `LOG_LEVEL`.

## R12

SI `LOG_LEVEL` no está definida o su valor no es uno de los niveles estándar ENTONCES el sistema DEBE usar `info` como nivel efectivo.

## R13

El sistema NO DEBE escribir en los logs la cadena de conexión ni credenciales de la base de datos.

## R14

El sistema NO DEBE exponer la `DATABASE_URL` al cliente: la variable no lleva prefijo `NEXT_PUBLIC_` y solo se lee desde módulos de servidor.

## R15

El sistema DEBE actualizar `web/AGENTS.md` (la constitución del frontal para agentes) con el scaffold hecho (stack y comandos), el BFF (`app/api/` como única frontera de datos), el rol `votoscope_web` (privilegios y contraseña por entorno) y la estrategia de tests y logging de la web.

## R16

El sistema DEBE actualizar `.agents/conventions.md` con la estrategia de tests de la web (runner `node --test`, `web/tests/`, herméticos y live con skip), la regla del BFF (`app/api/`, nada de SQL fuera), la implementación del logging de la web y las dependencias aprobadas de la web con pnpm.

## R17

El sistema DEBE actualizar `.agents/architecture.md` y `.agents/environment.md` para que la web figure como scaffold hecha (comandos de desarrollo y rol de solo lectura), sin afirmaciones obsoletas del tipo «Pendiente de scaffold».

## R18

El sistema DEBE configurar Tailwind CSS y shadcn/ui en `web/` —`components.json`, `web/components/ui/`, `web/lib/utils.ts` con `cn` y las variables de tema en `app/globals.css`— con al menos un componente de shadcn renderizado en la portada y las dependencias asociadas aprobadas en `design.md`.

## R19

El sistema DEBE incluir `web/README.md` como guía de arranque del frontal: requisitos (Node ≥ 24 y pnpm), instalación y `.env.local`, comandos (`pnpm dev`, `build`, `start`, `lint`, `test`), estructura, rol `votoscope_web`, BFF (`app/api/`), sistema de UI (Tailwind + shadcn) y enlace al contrato `docs/db/gold.md`, sin duplicar el detalle operativo de `web/AGENTS.md`.

## Correspondencia acceptance ↔ requirements

| Criterio de `acceptance` (feature_list.json) | Requirements |
| --- | --- |
| «app Next.js (App Router) en web/ con BFF obligatorio en app/api/: toda consulta a gold.* y a servicios externos vive ahí y el navegador nunca ve llamadas ni credenciales de BD» | R1, R2, R3, R4; credenciales en servidor: R14 |
| «rol de Postgres de solo lectura (SELECT solo sobre gold) creado por migración» | R5, R6, R7, R8, R9 |
| «logging por niveles con LOG_LEVEL en servidor» | R10, R11, R12, R13 |
| «web/AGENTS.md y .agents/conventions.md actualizados (estrategia de tests y logging)» | R15, R16 |
| Extra: coherencia de los docs de contexto que citan la web como pendiente | R17 |
| Extra: sistema de UI del proyecto (Tailwind + shadcn/ui) configurado en el scaffold | R18 |
| Extra: guía de arranque del frontal (`web/README.md`) | R19 |

## Notas de alcance

- **El contrato `gold` no se redefine**: las consultas de la web usan los nombres de vista y de columna de [`docs/db/gold.md`](../../docs/db/gold.md) / [`specs/015_delivery_gold/design.md`](../015_delivery_gold/design.md); si falta un dato para una pantalla, se añade la vista en el ingestador (feature futura), nunca se lee `silver` desde la web.
- **El BFF es la frontera de confianza**: `web/app/api/` es el único sitio con acceso a PostgreSQL o a servicios externos. Las páginas y componentes consumen el servicio del BFF en servidor; el navegador solo puede llamar a los Route Handlers `/api/*`, que devuelven JSON de `gold` y nunca SQL, cadenas de conexión ni errores internos. Un test estructural falla si aparece SQL o `pg` fuera de `app/api/`.
- **El scaffold no construye las pantallas**: la portada demuestra el camino completo (Server Component → servicio del BFF → vistas `gold` → HTML). Las pantallas del MVP (resultados por área/mesa, sondeos) son features posteriores sobre este scaffold.
- **El rol no es una tabla**: no toca el ERD ni `models.py`; vive solo en la migración (ver `design.md`, §La regla de oro).
- **Sin dependencias no aprobadas**: `design.md` lista las propuestas para el gate humano; el runner de tests es el nativo de Node (`node --test`), sin framework. Las dependencias de Tailwind y shadcn (R18) son las del CLI oficial con los componentes usados, no una elección ad-hoc.
- **shadcn/ui es la base visual del MVP**: el scaffold configura el sistema (tokens, `components.json`, `components/ui/`) y lo demuestra en la portada; las pantallas posteriores añaden componentes con `pnpm dlx shadcn@latest add`, sin introducir otra librería de UI.
- **Dos documentos del frontal**: `web/README.md` es la guía de arranque para humanos y `web/AGENTS.md` la constitución para agentes; no se solapan (el README no repite reglas de proceso y AGENTS no duplica el quickstart).
- La cola ejecuta la feature 17 después: el **README raíz** y `.agents/status.md` son suyos; esta feature no los toca (el README del paquete web sí, R19).

## Nota de verificación

- R1, R4, R14: `web/tests/structure.test.ts` (hermético: lee `package.json`, el árbol de `app/`, los fuentes de `lib/` y de `app/api/`; falla si hay SQL o `pg` fuera de `app/api/`) y `web/tests/bff.test.ts` (Route Handlers y validación de `electionId`).
- R18: `web/tests/structure.test.ts` (hermético: `components.json`, `components/ui/` no vacío, `lib/utils.ts` con `cn`, `globals.css` con Tailwind, la portada importa un componente de `@/components/ui/`, `pnpm-lock.yaml` sin `package-lock.json` y dependencias de shadcn en `package.json`).
- R2: `web/tests/gold_contract.test.ts` (hermético; SQL exportado por `app/api/_lib/gold.ts` contra los nombres del contrato) y `web/tests/gold_live.test.ts` (live con skip).
- R3: `web/tests/structure.test.ts` (la portada importa el servicio del BFF y es Server Component) y `web/tests/gold_live.test.ts` (las consultas devuelven los datos de la base local); el render se comprueba además con el smoke de `pnpm dev` documentado en `progress/impl_web_scaffold.md`.
- R5–R8: `ingestor/tests/test_web_role.py` (live contra el Postgres local; se saltan sin base, sin migrar o sin rol) — atributos del rol, grants de `gold`, privilegios por defecto y denegaciones fuera de `gold`.
- R9: `ingestor/tests/test_web_role.py` (la migración no contiene credenciales) y `web/tests/docs.test.ts` (los pasos de `ALTER ROLE` están documentados en `web/AGENTS.md`).
- R10–R12: `web/tests/logging.test.ts` (hermético; sink inyectado).
- R13: `web/tests/gold_live.test.ts` (captura de consola con `LOG_LEVEL=debug` durante una consulta real).
- R15–R17, R19: `web/tests/docs.test.ts` (hermético; subcadenas estables en los cinco documentos).
- Los tests de la web se ejecutan con `pnpm test` (`node --test`; ver estrategia en `design.md`), no con pytest: la feature actualiza `.agents/conventions.md` precisamente para fijar ese reparto (pytest para el ingestador y la BD; `node --test` para `web/`).
