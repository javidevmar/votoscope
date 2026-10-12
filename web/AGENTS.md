# AGENTS.md — web

Contexto del frontend. Antes de tocar nada, lee también el `AGENTS.md` de la raíz del repo.

## Qué es

Frontend del agregador, en Next.js (App Router). Consume las vistas del esquema `gold` de PostgreSQL directamente desde el servidor (Server Components). No hay API intermedia: los datos van de la base de datos a la web.

## Estado

Aún no hay scaffold. Próximo paso: crear la aplicación Next.js en este directorio. Hasta que existan las vistas `gold`, no hay datos que mostrar; el ingestador es la prioridad.

## Reglas

- **Solo lectura**: la web nunca escribe ni migra la base de datos; de eso se encarga el ingestador.
- Consultar las vistas `gold.*`, no las tablas `silver` directamente. Si falta un dato para una pantalla, se añade la vista en el ingestador (ERD ↔ modelos ↔ migración).
- Las credenciales de Postgres nunca llegan al cliente: los datos se leen en servidor.
- **Rol de BD**: al hacer el scaffold, la web usará un rol de Postgres de solo lectura (SELECT solo sobre `gold`), creado por migración como el resto del esquema.
- **Dependencias**: ninguna nueva sin consentimiento explícito del usuario (ver [`../.agents/conventions.md`](../.agents/conventions.md)).

## Logging

- Niveles estándar (debug/info/warn/error); nivel configurable por entorno: `LOG_LEVEL` en servidor (`NEXT_PUBLIC_LOG_LEVEL` solo si hiciera falta en cliente).
- Se implementa al hacer el scaffold, sin dependencias nuevas.
