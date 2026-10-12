# Planes de trabajo

Registro laxo de planes y especificaciones para agentes: continuidad entre sesiones, no documentación para terceros. Deliberadamente más ligero que spec-kit.

## Formato

Un fichero por iniciativa en este directorio. Cabecera corta y fija; cuerpo libre (notas, listas, bocetos):

```md
# Título
Estado: hecho · Creado: AAAA-MM-DD · Abierto: AAAA-MM-DD · Hecho: AAAA-MM-DD · Actualizado: AAAA-MM-DD
Objetivo: una frase.

## Notas
...
```

- `Creado`: fecha en que nace el fichero.
- `Abierto`: fecha en que el plan entra en trabajo (= `Creado` si nace abierto).
- `Hecho`: fecha de cierre (solo cuando `Estado: hecho`).
- `Actualizado`: fechas de las modificaciones del plan posteriores a la creación, separadas por comas (el cierre cuenta); se omite si no hay ninguna.

## Reglas

1. **Cuándo existe un plan**: si la tarea cabe en una sesión y toca una sola parte, no hay plan — se hace. Nace cuando cruza sesiones o define una frontera entre partes (gold↔front, parser↔silver, ERD↔modelos).
2. **Ciclo de vida**: `abierto` → `hecho` (o `descartado`). Al cerrar, lo durable se pliega a los docs tema (`.agents/*.md`) y el plan **se conserva** aquí con `Estado: hecho` y sus fechas: es el registro de lo ejecutado y nunca se borra. Un plan cerrado no se edita salvo para corregir sus fechas.
3. **Enlace**: los pendientes de [`../status.md`](../status.md) apuntan a su plan cuando exista; al arrancar sesión se lee solo el índice y el plan solo cuando toca esa tarea.
4. **Contenido**: prosa en español, en bruto. Nada de plantillas, carpetas por estado, numeración ni checklists.
