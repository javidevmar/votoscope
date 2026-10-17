# Spec Driven Development (SDD)

Contexto para agentes IA. Índice general: [`../AGENTS.md`](../AGENTS.md).

> Flujo Kiro-style: requirements → design → tasks → código.
> El código no se escribe hasta que el spec está aprobado por un humano.

## Estructura

Cada feature nueva (`"sdd": true` en [`../feature_list.json`](../feature_list.json)) tiene una carpeta dedicada en cuanto deja `pending`:

```
specs/<feature-name>/
├── requirements.md   # QUÉ se necesita (EARS)
├── design.md         # CÓMO se construirá (decisiones técnicas)
└── tasks.md          # PASOS concretos a implementar
```

El `<feature-name>` coincide con el campo `name` de `feature_list.json`.

## Estados de una feature

| Estado | Significado |
| --- | --- |
| `pending` | Sin spec. El `spec-author` es el primero en actuar. |
| `spec_ready` | Spec redactado. Esperando aprobación humana. NO se toca código. |
| `in_progress` | Spec aprobado. `implementer` trabajando. |
| `done` | Código verde, `reviewer` aprobó, sesión cerrada. |
| `blocked` | Atascado. Razón en `progress/current.md`. |

## La puerta de aprobación humana

El flujo automático se detiene **una vez**: cuando el `spec-author` termina sus tres archivos, marca la feature como `spec_ready` y para. El humano lee `specs/<feature>/` y dice «aprobado» (o pide cambios).

Solo entonces el `leader` transiciona `spec_ready → in_progress` y lanza el `implementer`.

```
pending → [spec-author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

## requirements.md — EARS estricto

Cada requirement es un párrafo numerado con uno de estos cinco patrones:

| Patrón | Plantilla |
| --- | --- |
| **Ubicuo** | `El sistema DEBE <acción>.` |
| **Evento** | `CUANDO <disparador>, el sistema DEBE <acción>.` |
| **Estado** | `MIENTRAS <estado>, el sistema DEBE <acción>.` |
| **Opcional** | `DONDE <feature opcional>, el sistema DEBE <acción>.` |
| **No deseado** | `SI <evento no deseado> ENTONCES el sistema DEBE <acción>.` |

Reglas duras:

- Cada requirement tiene un id estable: `R1`, `R2`, …
- Cada requirement DEBE ser verificable por al menos un test concreto.
- No mezcles varios `DEBE` en un mismo requirement. Si hay más de uno, parte.
- No uses verbos blandos («podría», «puede», «soporta»). Solo `DEBE` / `NO DEBE`.
- Cada criterio del `acceptance` de `feature_list.json` DEBE quedar cubierto por al menos un `R<n>`; deja la tabla de correspondencia al final.

Ejemplo:

```markdown
## R1
CUANDO el usuario ejecuta `uv run ingestor ingest-polls` y hay un snapshot
nuevo, el sistema DEBE cargar sus sondeos en `silver` en una transacción.

## R2
SI la revisión del snapshot es anterior a la ya cargada ENTONCES el sistema
DEBE ignorarla con un warning y salir con exit code 0.
```

## design.md — decisiones técnicas

Captura **antes** de tocar código:

- Qué archivos se crean / modifican.
- Qué firmas nuevas aparecen (funciones, clases, comandos).
- Qué excepciones se reutilizan o se añaden.
- Qué alternativa se descartó y por qué (mínimo una).
- Si la feature toca el modelo de datos: los tres sitios de la regla de oro (ERD ↔ `models.py` ↔ migración) y el detalle concreto de cada uno.

NO es ingeniería desde primeros principios: apóyate en [`architecture.md`](architecture.md), [`conventions.md`](conventions.md) y [`style.md`](style.md). El `design.md` documenta los puntos donde la feature roza la frontera de esas reglas.

## tasks.md — checklist ejecutable

Pasos discretos en orden, cada uno con checkbox. Cada task referencia al menos un `R<n>` que cubre.

```markdown
- [ ] T1 — Añadir `cmd_ingest_polls` en `src/ingestor/cli.py`. Cubre: R1.
- [ ] T2 — Registrar el subcomando `ingest-polls`. Cubre: R1, R2.
- [ ] T3 — Añadir `test_polls_load_*` en `tests/test_polls.py`. Cubre: R1–R3.
```

El `implementer` marca `[x]` cada task al completarla. El `reviewer` rechaza si queda alguna `[ ]` sin justificación documentada.

## Trazabilidad (regla dura)

- Cada test afectado en `ingestor/tests/` debe poder mapearse a un `R<n>` de su spec.
- Cada `R<n>` debe tener al menos un test concreto.
- El `reviewer` comprueba esta correspondencia explícitamente y rechaza si falta.

El `implementer` documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_ingest_polls_loads_snapshot`
- R2 → `test_ingest_polls_ignores_older_revision`
```

## Cuándo NO aplica SDD

- Features con `"sdd": false` o sin el campo `sdd`: son las ya terminadas (1–4) y no tienen spec. SDD solo se aplica hacia adelante.
- Cambios triviales que no llegan a feature (typos, ajustes de docs): se hacen directamente, sin spec.
- La skill `spec-driven-development` del repo es orientación general; el proceso vigente en este repositorio es este documento.
