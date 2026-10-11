# Planes de trabajo

Registro laxo de planes y especificaciones para agentes: continuidad entre sesiones, no documentación para terceros. Deliberadamente más ligero que spec-kit.

## Formato

Un fichero por iniciativa en este directorio. Cabecera corta y fija; cuerpo libre (notas, listas, bocetos):

```md
# Título
Estado: abierto · Creado: AAAA-MM-DD
Objetivo: una frase.

## Notas
...
```

## Reglas

1. **Cuándo existe un plan**: si la tarea cabe en una sesión y toca una sola parte, no hay plan — se hace. Nace cuando cruza sesiones o define una frontera entre partes (gold↔front, parser↔silver, ERD↔modelos).
2. **Ciclo de vida**: `abierto` → `hecho` (o `descartado`) → se pliega. Al cerrar, lo durable se mueve a los docs tema (`.agents/*.md`) y el plan **se borra**; el historial queda en git. Sin archivo de planes muertos.
3. **Enlace**: los pendientes de [`../status.md`](../status.md) apuntan a su plan cuando exista; al arrancar sesión se lee solo el índice y el plan solo cuando toca esa tarea.
4. **Contenido**: prosa en español, en bruto. Nada de plantillas, carpetas por estado, numeración ni checklists.
