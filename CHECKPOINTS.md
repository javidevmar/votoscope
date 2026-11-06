# CHECKPOINTS — final state evaluation

Use this before declaring a feature `done`. `./init.sh` is the executable gate;
this file is the human/agent checklist. A checked box means the condition is
true for the current working tree, not that it was true at some point.

## C1 — The harness is complete

- [ ] `AGENTS.md`, `CHECKPOINTS.md`, `harness.config.json`, `init.sh` and
      `.agents/specs.md` exist. With `feature_queue: true` (target projects),
      `feature_list.json`, `progress/current.md` and `progress/history.md`
      also exist.
- [ ] The six agents exist in `.opencode/agents/`: `leader`, `spec-author`,
      `test-generator`, `implementer`, `reviewer`, `github-handler`.
- [ ] The two commands exist in `.opencode/commands/`: `next-feature`,
      `close-session`.
- [ ] `./init.sh` exits with code 0.

## C2 — State is coherent (target projects, `feature_queue: true`)

- [ ] At most `agents.max_features_in_progress` features are `in_progress`
      (default: 1).
- [ ] Every `done` feature has green checks.
- [ ] Every feature id and name is unique; every status is valid.
- [ ] `progress/current.md` is empty or describes only the active session (no
      leftovers from previous sessions).
- [ ] `progress/history.md` has one entry per closed session.

## C3 — The code respects the repo rules

- [ ] Layers and boundaries follow `.agents/architecture.md`.
- [ ] Naming, logging, errors and security follow `.agents/conventions.md`.
- [ ] Formatting and language conventions follow `.agents/style.md`.
- [ ] No new dependency without explicit user consent.
- [ ] No secrets in code, logs, docs or fixtures.
- [ ] No debug prints, temporary files or context-free TODOs.
- [ ] If the project has a schema or generated artifacts, every source of truth
      is updated together (for example ERD ↔ models ↔ migration).
- [ ] Documentation affected by the change is updated in the same change.

## C4 — Verification is real

- [ ] `./init.sh` is green, including every `required: true` check in
      `harness.config.json`.
- [ ] At least one real project check is configured.
- [ ] The feature has tests (or a documented manual verification where a test
      cannot reach the behavior).
- [ ] No unexplained skipped tests.
- [ ] Test-generator exclusively authored tests/assets and the full persistent
      handoff; leader read and forwarded its exact marker plus unchanged contract.
      Meaningful RED was reproduced before production code, or docs-only N/A
      was explicitly approved. GREEN and inventory/SHA unchanged against contract
      baselines (not HEAD) are recorded in the implementation report.
- [ ] Test corrections/additional coverage went through leader to test-generator
      before refreshed handoff/resume; implementer never edited tests/handoff.
- [ ] CI is green for the working branch, if CI exists.
- [ ] Manual checks are reproducible and documented in
      `progress/impl_<name>.md`.

## C5 — The session closed well

- [ ] No temporary files, caches or untracked junk outside `.gitignore`.
- [ ] In a target project, `progress/history.md` has an entry for the session.
- [ ] In a target project, `feature_list.json` reflects the real state.
- [ ] Commits are atomic, conventional and made only with explicit user
      approval, executed by `github-handler` from leader context.
- [ ] The branch is correct; no push happened without explicit user approval.
      Only `github-handler` ran state-changing git/gh commands, and it was
      launched only with prior explicit user permission.
- [ ] The working tree contains only the intended changes.

## C6 — Spec Driven Development

- [ ] Every `sdd: true` feature in `spec_ready`, `in_progress` or `done` has
      `specs/<NNN>_<name>/requirements.md`, `design.md` and `tasks.md`.
- [ ] `requirements.md` uses strict EARS (see `.agents/specs.md`) and every
      acceptance criterion from `feature_list.json` maps to at least one
      `R<n>`.
- [ ] The `Demo` in `design.md` was exercised and crosses every layer declared in
      `Layers`, or `Enabler: yes` records why it cannot be divided.
- [ ] Every `R<n>` has at least one concrete test or an approved, documented
      verification method.
- [ ] For SDD work, `specs/<NNN>_<name>/tests.md` maps every `R<n>` and `T<n>` to
      the test(s) that prove it (or an approved N/A).
- [ ] Every task in `tasks.md` is `[x]` for a `done` feature. If a task cannot
      be completed, amend the spec and get reviewer approval; do not leave an
      unchecked box.
- [ ] `progress/impl_<name>.md` contains the `R<n> → test` map.
- [ ] `progress/review_<name>.md` exists and the reviewer verdict is
      `APPROVED`.

## C7 — Optional epics and branch/PR evidence

- [ ] When `initiative` groups an epic, generation AND implementation followed
      ascending feature `id`, with no parallel tasks/features; predecessor
      review/user gates, checks and authorized commits finished before successors
      (PR merge was not required).
- [ ] Branch preparation follows `.agents/specs.md#epics-and-stacked-prs`:
      selected remote fetched, `development` preferred, otherwise `main`/`master`
      resolved by remote default; base/predecessor safely fast-forwarded with
      recorded SHAs. No dirty/divergent/ambiguous state was bypassed or work lost.
- [ ] Branch parent matches actual PR state, not ancestry alone: previous
      unmerged feature branch, or updated base after merge (including squash/rebase).
- [ ] After authorized pushes, `github-handler` creates one PR per feature
      targeting the previous unmerged feature or base, with epic/ordered PR links
      and verification context; no aggregate epic PR. The leader verifies remote
      head/base/state; after parent merge, the successor base is
      reconciled/retargeted and its diff checked before proceeding.
- [ ] Push/PR actions not yet authorized are explicitly pending, not fabricated;
      commit/push gates remain and no merge permission was inferred.

## Project-specific checkpoints

Add project-specific conditions here or in `.agents/conventions.md`. Keep them
objective and executable where possible. The generic boxes above are the floor,
not the ceiling.
