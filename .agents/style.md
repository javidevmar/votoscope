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

## Frontend

- Por definir al hacer el scaffold de `web/`.
