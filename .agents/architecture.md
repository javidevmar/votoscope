# Arquitectura

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

## Qué es

Votoscope es un agregador de resultados electorales de España.

- **MVP**: las últimas elecciones generales (Congreso), con resultados por **mesa** (la unidad más fina publicada), a partir de ficheros fuente descargados en local.
- **Diseño extensible**: después, Senado, procesos anteriores y elecciones autonómicas/municipales, sin rehacer el esquema.

## Dos partes

1. **Ingestador — `ingestor/` (Python)**: pipeline bronce → plata → oro sobre PostgreSQL.
   - **Bronce**: ficheros originales, inmutables, en `data/raw/`, más un registro por fichero en `bronze.ingesta` (ruta, sha256, tamaño, fuente, estado). Un fichero corregido entra como fichero nuevo.
   - **Plata**: tablas normalizadas en el esquema `silver`. Sin agregados.
   - **Oro**: vistas en el esquema `gold`, una por consulta del frontend. Pendientes de crear.
2. **Frontend — `web/` (Next.js)**: lee las vistas `gold` directamente de PostgreSQL, en servidor (Server Components). Sin API intermedia: solo dos partes. Pendiente de scaffold.

## Flujo de datos

```
data/raw/  →  bronze.ingesta (registro)  →  silver (normalizado)  →  gold (vistas)  →  web/
```

El ingestador no descarga nada: trabaja sobre los ficheros que haya en `data/raw/`.

## Mapa del repositorio

```
.
├── AGENTS.md                  ← enrutador
├── .agents/                   ← documentación por temas (este directorio)
├── README.md
├── docker-compose.yml         ← Postgres 18 local (host: 5433)
├── data/
│   └── raw/                   ← ficheros fuente (bronce, gitignored)
├── docs/
│   └── db/schema.drawio       ← ERD de referencia
├── ingestor/                  ← ingestador Python (ver ingestor/AGENTS.md)
└── web/                       ← frontend Next.js (ver web/AGENTS.md)
```
