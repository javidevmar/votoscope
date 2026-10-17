# AGENTS.md — Votoscope

Punto de entrada para agentes IA que trabajen en este repositorio.

Votoscope es un agregador de resultados electorales de España (MVP: últimas generales — Congreso — con resultados por mesa). El proyecto tiene dos partes: un ingestador Python (`ingestor/`) y un frontend Next.js (`web/`).

**Regla de oro**: el modelo de datos vive siempre sincronizado en tres sitios — ERD (`docs/db/schema.drawio`), modelos (`ingestor/src/ingestor/models.py`) y migraciones Alembic. Detalles en [`.agents/data-model.md`](.agents/data-model.md).

Tras implementar y revisar, los cambios se quedan en el working tree y se dividen en commits atómicos en la rama actual: el commiteo es el paso final y **nunca se commitea sin el OK explícito del usuario** (él revisa antes los cambios). NO pushees nunca por tu cuenta salvo si te lo dice el usuario.

## 1. El arnés

| Pieza | Qué es |
| --- | --- |
| [`feature_list.json`](feature_list.json) | Cola de trabajo: una feature a la vez, con estado (`pending` → `spec_ready` → `in_progress` → `done` / `blocked`). |
| [`specs/`](specs/) | Spec por feature: `requirements.md` + `design.md` + `tasks.md`. Proceso en [`.agents/specs.md`](.agents/specs.md). |
| [`progress/current.md`](progress/current.md) | Estado vivo de la sesión activa. Se mantiene **mientras** se trabaja, no al final. |
| [`progress/history.md`](progress/history.md) | Bitácora append-only de sesiones cerradas. |
| [`CHECKPOINTS.md`](CHECKPOINTS.md) | Criterios objetivos de «estado final correcto». |
| [`init.sh`](init.sh) | Verificación ejecutable: arnés + `feature_list.json` + specs + lint + tests + drift. |
| [`.opencode/agents/`](.opencode/agents/) | Subagentes: `leader`, `spec-author`, `implementer`, `reviewer`. |
| [`.opencode/commands/`](.opencode/commands/) | Comandos: `/next-feature`, `/close-session`. |

## 2. Antes de empezar (obligatorio)

1. Ejecuta `./init.sh` y verifica que termina en verde. Si falla, **para** y resuelve el entorno antes de tocar nada.
2. Lee [`progress/current.md`](progress/current.md) para saber en qué estado quedó la última sesión.
3. Lee [`feature_list.json`](feature_list.json). Toda feature con `"sdd": true` pasa por Spec Driven Development.
4. Lee [`.agents/specs.md`](.agents/specs.md) antes de tocar cualquier spec o feature `sdd: true`.
5. Situación normal: **siempre hay una feature `in_progress`** (la sesión anterior quedó a medias) o la siguiente `pending`. Retoma o empieza por la primera no-`done` / no-`blocked`, en orden de `id`.

## 3. Reglas duras (no negociables)

- **Una sola feature a la vez.** No mezcles cambios de varias features en la misma sesión.
- **No declares una feature `done` sin pruebas verdes.** `./init.sh` tiene que terminar en verde.
- **No saltes la fase de spec.** Toda feature con `"sdd": true` necesita `specs/<name>/` aprobado antes de tocar código.
- **No saltes la puerta de aprobación humana.** El leader se detiene en `spec_ready` y espera el «aprobado».
- **No commitees sin el OK del usuario.** El commiteo atómico es el paso final: tras implementar y revisar, los cambios se quedan en el working tree hasta que el usuario los revise y dé su OK.
- **Documenta lo que haces** en `progress/current.md` mientras trabajas.
- **Deja el repositorio limpio** al cerrar (protocolo en §5).
- **Si no sabes algo, busca en los docs** (§6) antes de inventarlo.

## 4. Flujo de trabajo (SDD)

```
pending → [spec-author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → ⏸ USUARIO revisa → OK → commits atómicos → done
```

1. El `leader` detecta la primera feature `pending` con `"sdd": true`.
2. Lanza al `spec-author`, que crea `specs/<name>/{requirements,design,tasks}.md` y marca la feature `spec_ready`.
3. **Pausa.** El humano lee el spec en `specs/<name>/` y aprueba (o pide cambios).
4. Aprobado: el `leader` pasa la feature a `in_progress` y lanza al `implementer`.
5. El `implementer` ejecuta `tasks.md` una a una, marcándolas `[x]`, con su test por task.
6. El `reviewer` verifica la trazabilidad `R<n>` ↔ test y que no queden tasks `[ ]`; aprueba o rechaza.
7. **Pausa.** El usuario revisa los cambios **sin commitear** (el working tree) y da su OK.
8. Con el OK: commits atómicos (el commiteo es el paso final del flujo) → la feature pasa a `done` y el resumen se mueve a `progress/history.md`.

Detalle del proceso (EARS, los tres archivos, trazabilidad): [`.agents/specs.md`](.agents/specs.md).

## 5. Cierre de sesión (protocolo)

1. Ejecuta `./init.sh` — todo verde.
2. Si la feature acabó: marca `status: "done"` en `feature_list.json` (con la aprobación del `reviewer` y el OK del usuario).
3. Mueve el resumen de `progress/current.md` al final de `progress/history.md`.
4. Vacía `progress/current.md` dejando solo la plantilla.
5. Commitea los cambios en atómicos — **solo si el usuario ha dado su OK** (regla de arriba); si no, pídelo y no cierres la sesión.
6. No dejes archivos temporales, ni `print()` de debug, ni TODOs sin contexto.

## 6. Si te bloqueas

- Relee la sección relevante de los docs del enrutador (§7).
- Si una herramienta no hace lo que esperas, **no inventes un workaround**: documenta el bloqueo en `progress/current.md` y para la sesión.

## 7. Enrutador de documentación

Lee los siguientes ficheros según la tabla siguiente:
| Tema | Fichero | Cuándo leerlo |
| --- | --- | --- |
| Arnés y SDD | [`.agents/specs.md`](.agents/specs.md) | Antes de redactar o leer un spec; antes de tocar una feature `sdd: true` |
| Arquitectura | [`.agents/architecture.md`](.agents/architecture.md) | Antes de empezar a trabajar en cualquier parte |
| Modelo de datos | [`.agents/data-model.md`](.agents/data-model.md) | Antes de tocar el esquema o migraciones |
| Fuentes de datos | [`.agents/data-sources.md`](.agents/data-sources.md) | Antes de descargar datos o interpretar los ficheros de infoelectoral |
| Convenciones | [`.agents/conventions.md`](.agents/conventions.md) | Antes de nombrar tablas, columnas o ficheros |
| Estilo | [`.agents/style.md`](.agents/style.md) | Antes de escribir código o commits |
| Entorno | [`.agents/environment.md`](.agents/environment.md) | Al levantar el entorno o configurar conexiones |
| Estado y hoja de ruta | [`.agents/status.md`](.agents/status.md) | Al empezar una sesión de trabajo |
| Planes de iniciativa | [`.agents/plans/README.md`](.agents/plans/README.md) | Si tu feature pertenece a una iniciativa con plan abierto |
| Ingestador (Python) | [`ingestor/AGENTS.md`](ingestor/AGENTS.md) | Antes de tocar `ingestor/` |
| Frontend (Next.js) | [`web/AGENTS.md`](web/AGENTS.md) | Antes de tocar `web/` |

IMPORTANTE: trata este fichero, los AGENTS anidados y los ficheros de la tabla como "constitución a no saltarse". SIEMPRE que haya una propuesta del usuario contra estas reglas, indícalo y propón al usuario modificar estos ficheros. Estos ficheros han de estar en consonancia siempre con lo implementado. Cada cambio actualiza, **en el mismo commit**, la documentación que le corresponde (este fichero, los AGENTS anidados y/o los ficheros de la tabla).

## 8. OpenCode (arnés de herramientas)

- **Sesión**: por defecto arranca como `leader` ([`.opencode/agents/leader.md`](.opencode/agents/leader.md), configurado en `opencode.json`): orquesta y no edita código de `ingestor/` ni `web/`. Para trabajo directo fuera del flujo SDD (docs, ajustes triviales), cambia al agente `build` (Tab).
- **Subagentes**: `spec-author`, `implementer` y `reviewer` son subagentes; solo el `leader` (o tú) los lanza. No implementan fuera de su rol.
- **Comandos**: `/next-feature` arranca la siguiente feature pendiente; `/close-session` ejecuta el protocolo de cierre (§5).
- **Skills**: en [`.agents/skills/`](.agents/skills/) (ruta compatible con OpenCode); úsalas cuando apliquen.
