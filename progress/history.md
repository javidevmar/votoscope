# Bitácora histórica (append-only)

Las sesiones anteriores al arnés SDD están registradas en `.agents/plans/` y en el historial de git.

---

## 2026-10-17 — Bootstrap del arnés SDD (OpenCode)

- **Agente:** humano + OpenCode (rama `feature/sdd-harness`).
- **Plan:** portar el arnés de referencia (harness-sdd) a Votoscope con convenciones de OpenCode: cola de features, specs (requirements/design/tasks), subagentes y verificación ejecutable.
- **Cambios:** `AGENTS.md` (reglas, flujo SDD y sección OpenCode), `feature_list.json` (4 features hechas + 10 pendientes), `CHECKPOINTS.md`, `.agents/specs.md`, `.opencode/agents/{leader,spec-author,implementer,reviewer}.md`, `.opencode/commands/{next-feature,close-session}.md`, `opencode.json`, `progress/` e `init.sh`.
- **Verificación:** `./init.sh` verde.
- **Cierre:** arnés listo. Siguiente: feature 5 `polls_model` (spec primero; contexto en `.agents/plans/polls-wikipedia.md`).
