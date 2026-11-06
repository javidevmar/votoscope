---
description: Close the session (init.sh, bitácora and clean state)
agent: leader
---

Before touching `feature_list.json` or `progress/`, ask the user for explicit
approval. Without it, stop without changing anything and ask them to review the
working tree.

With approval, close the session following the §6 protocol of `AGENTS.md`:

1. Run `./init.sh`.
2. Leave `feature_list.json` in its real state (`done` only with reviewer
   approval and user OK).
3. Move the summary from `progress/current.md` to `progress/history.md`.
4. Leave `progress/current.md` with only the template / next step.
5. Launch `github-handler` to commit atomically only with prior explicit user
   approval. Never push without explicit approval. Accept only `OK` or
   `KO: <reason>` from it.
