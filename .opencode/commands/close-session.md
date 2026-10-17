---
description: Cierra la sesión (init.sh, bitácora y estado limpio)
agent: leader
---

Cierra la sesión siguiendo el protocolo de cierre de `AGENTS.md` §5: ejecuta `./init.sh`, deja `feature_list.json` en su estado correcto, mueve el resumen de `progress/current.md` a `progress/history.md`, vacía la sesión actual y commitea los cambios.
