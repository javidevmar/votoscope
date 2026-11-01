# AGENTS.md — web

Contexto del frontend. Antes de tocar nada, lee también el `AGENTS.md` de la raíz del repo.

Proceso: toda feature con `sdd: true` en [`../feature_list.json`](../feature_list.json) pasa por su spec en `../specs/<name>/` antes de tocar código; ver [`../AGENTS.md`](../AGENTS.md) y [`../.agents/specs.md`](../.agents/specs.md).

## Qué es

Frontend del agregador, en Next.js (App Router). Consume las vistas del esquema `gold` a través de un **BFF obligatorio** en `app/api/`: toda consulta a PostgreSQL o a servicios externos vive ahí y el navegador nunca recibe credenciales ni SQL. Las páginas se renderizan en servidor (Server Components).

## Estado

Aún no hay scaffold. Próximo paso: crear la aplicación Next.js en este directorio. Las vistas `gold` ya existen; el contrato pantalla ↔ vista está en [`../docs/db/gold.md`](../docs/db/gold.md).

## Reglas

- **Solo lectura**: la web nunca escribe ni migra la base de datos; de eso se encarga el ingestador.
- **BFF obligatorio**: toda llamada a PostgreSQL o a servicios externos vive bajo `web/app/api/`; las páginas y componentes no importan `pg` ni contienen SQL. El navegador solo puede llamar a los Route Handlers `/api/*` (nunca a la base).
- Consultar las vistas `gold.*`, no las tablas `silver` directamente. Si falta un dato para una pantalla, se añade la vista en el ingestador (ERD ↔ modelos ↔ migración). Contrato de datos: [`../docs/db/gold.md`](../docs/db/gold.md).
- Las credenciales de Postgres nunca llegan al cliente: los datos se leen en servidor.
- **Rol de BD**: al hacer el scaffold, la web usará un rol de Postgres de solo lectura (SELECT solo sobre `gold`), creado por migración como el resto del esquema.
- **Dependencias**: ninguna nueva sin consentimiento explícito del usuario (ver [`../.agents/conventions.md`](../.agents/conventions.md)).

## Logging

- Niveles estándar (debug/info/warn/error); nivel configurable por entorno: `LOG_LEVEL` en servidor (`NEXT_PUBLIC_LOG_LEVEL` solo si hiciera falta en cliente).
- Se implementa al hacer el scaffold, sin dependencias nuevas.
