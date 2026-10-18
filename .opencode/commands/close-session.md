---
description: Cierra la sesión (init.sh, bitácora y estado limpio)
agent: leader
---

Antes de tocar `feature_list.json` o `progress/`, pide al usuario su OK explícito. Si no lo tienes, para sin cambiar nada y pide que revise los cambios. Con el OK, cierra la sesión siguiendo el protocolo de `AGENTS.md` §5: ejecuta `./init.sh`, deja `feature_list.json` en su estado correcto, mueve el resumen de `progress/current.md` a `progress/history.md` y vacía la sesión actual. El commiteo atómico es el paso final: solo con el OK explícito del usuario; nunca commitees sin él.
