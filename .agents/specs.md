# Spec Driven Development (SDD)

Context for AI agents. General index: [`../AGENTS.md`](../AGENTS.md).

This workflow ships to target projects. The harness source repo runs with
`feature_queue: false` and has no queue or spec folders of its own.

## Structure

Every new feature with `"sdd": true` gets a dedicated folder as soon as it
leaves `pending`:

```text
specs/<NNN>_<name>/
├── requirements.md   # WHAT is needed (strict EARS)
├── design.md         # HOW it will be built (technical decisions)
├── tasks.md          # concrete, ordered steps
└── tests.md          # requirement/task -> tests table (test-generator)
```

The folder name is `<NNN>_<name>`: the feature `id` from `feature_list.json`
with three digits (zero-padded) and its `name` field, for example
`specs/006_polls_fetch/`.

`tests.md` is not written by `spec-author`: `test-generator` creates it once
the tests exist (see [Test generation and handoff](#test-generation-and-handoff)).
Direct `sdd: false` work has no spec folder and keeps its mapping in the
persistent handoff contract.

## Design context

There are no separate initiative documents. Durable context lives in the
**topic docs** (`.agents/*.md`, routed from [`../AGENTS.md`](../AGENTS.md) §8)
and in each feature's `acceptance` list in `feature_list.json`. The
`spec-author` reads those and absorbs into the spec whatever the feature needs;
a spec references only topic docs, sibling specs and code.

## Vertical slices (default)

A vertical slice is the default scope: a feature should be one thin, demoable
end-to-end increment, and its `acceptance` describes observable behavior;
"migration created" or "endpoint added" is not an acceptance criterion.

The default is not a mandate. When the work cannot be divided into a demoable
slice — an indivisible refactor, a hotfix, an initial migration, auth
bootstrap, a design system — it may ship as one feature. Record why in
`design.md` (`Enabler: yes` plus the reason) and keep it minimal.

Every spec declares a slice contract in `design.md` before `## Files`:
`Entry point` (how a user or demo reaches the increment), `Layers` (layers
traversed, in order), `Demo` (one executable command or scripted walkthrough)
and `Enabler` (`no`, or `yes` plus the reason it cannot be sliced and, when
applicable, the next feature that consumes it).

`tasks.md` starts with one walking-skeleton task: entry point → data → response,
minimal and possibly stubbed. The skeleton is one task, not a layer checklist.
Later tasks widen it. Each behavioral task cycles through test-generator RED,
leader handoff and implementer minimal GREEN; do not turn this into horizontal
test/production layer batches.

Horizontal plans (all migrations, then all endpoints, then all UI) should be
split into slices in `feature_list.json`; when they cannot, the reason lives in
the feature's spec.

## Epics and stacked PRs

An epic is optional: features with the same `initiative` in `feature_list.json`
belong to one epic. Order is strictly ascending feature `id`, not array order;
there is no new registry or schema. Without `initiative`, work remains standalone.
Generate specs AND implement features/tasks sequentially: no parallel tasks or
features, no speculative generation of later epic specs. Finish the predecessor's
review and user gates, green checks and authorized commits before generating or
implementing its successor. A blocked predecessor blocks its successors; do not
skip it inside the epic. Do not wait for its PR to merge: an unmerged parent is
the point of a stack. SDD defaults and both human gates remain unchanged.

### Git and GitHub ownership

Only `github-handler` changes git or GitHub state. The `leader` inspects
read-only and passes the exact operation context to that subagent, which answers
only `OK` or `KO: <reason>`. The leader never launches it without prior explicit
user permission for the requested operation, including branch preparation.
Other agents may inspect (`git status`, `git diff`, `git log`, `gh pr view`) but
never fetch, branch, stage, commit, push or open a PR. Approval for commit, push
or PR remains separate and explicit.

### Branch preparation (before writing feature files)

The leader requests prior explicit user permission before delegating any branch
operation. No `github-handler` launch happens without it.

1. The leader inspects the working tree, current branch, local/remote refs and
   any recorded epic chain. Stop on a dirty working tree (including untracked
   work), an existing conflicting `feature/<name>`, divergent branches or
   ambiguous state. Never reset, auto-stash or discard user work. Select the
   remote explicitly from project configuration or the user's choice; do not
   guess among remotes. Pass `git fetch <remote>` to `github-handler` before
   creation; stop if it returns `KO`.
2. Select `development` if it exists locally OR on the selected remote.
   Otherwise select the existing `main` or `master`; if both exist, the selected
   remote default (verify symbolic HEAD with `git ls-remote --symref <remote> HEAD`)
   resolves the choice. If still
   ambiguous, or no usable base exists, stop and ask the user. If the chosen
   base exists only remotely, ask `github-handler` to create its local tracking
   branch. If it exists only locally, stop for clarification rather than claim a
   remote refresh.
3. For the first epic feature (and standalone work), `github-handler` checks out
   the selected local base, updates it with `git merge --ff-only <remote>/<base>`
   and creates `feature/<name>` from it, before spec or implementation edits.
   The handler verifies the result contains the fetched tip and preserves local
   commits if ahead; the leader records that fact. Divergence means stop, never
   reset.
4. For a successor, the leader inspects the predecessor's **actual PR state** on
   the selected remote/repository (read-only, for example
   `gh pr view <PR> --json state,mergedAt,baseRefName,headRefName,url`).
   Ancestry alone cannot detect squash or rebase merges. If it is OPEN and
   unmerged, `github-handler` checks out the previous feature branch, safely
   refreshes it with `git merge --ff-only <remote>/feature/<previous_name>`
   after fetching, and creates `feature/<name>`. Preserve local reviewed commits
   if ahead; stop if divergent or reviewed commits are missing. Verify the head
   matches the intended epic predecessor before creating the branch. If no PR
   exists yet, confirm its absence remotely, record the unpublished predecessor
   and branch from its verified reviewed local head; do not fabricate remote/PR
   evidence.
5. If the predecessor PR is MERGED, first update the selected base as in step 3
   and branch from it, not from the old feature tip. CLOSED without merge,
   unavailable PR state, unexpected heads/bases or ambiguity means stop.
   On resume, the leader verifies existing branch provenance read-only rather
   than recreate it.

Record the remote, base, ordered epic ids, branch names, relevant SHAs, PR
state/URLs and commands/results in `progress/current.md` and the implementation
report. Never silently rewrite published work. A squash/rebase merge can require
explicitly approved reconciliation of an existing successor; stop and propose
it rather than automatically rebasing or force-pushing.

### One PR per feature

Only after explicitly authorized pushes, the leader passes the PR context to
`github-handler`, which creates one PR per feature. The bottom PR targets the
selected base; each successor targets the previous unmerged feature branch. If
the predecessor has merged, target the updated base instead. There is no
aggregate epic PR. Ordinary
`gh pr create --base <parent-or-base> --head feature/<name>` is sufficient;
`gh-stack` is optional if already installed, never a required dependency.
Do not run bulk sync/rebase/push helpers that bypass these safety or approval gates.

Each PR body includes the epic identifier (`initiative`, or standalone), ordered
feature chain and known PR links (mark unpublished links pending), feature
id/name, spec path when applicable, verification commands/results and limitations.
The leader passes earlier PR context updates to `github-handler` as later PR
links become available. Verify actual remote PR heads, bases and state after
creation or edits, not only local metadata.

When a parent merges, verify/reconcile the successor PR base before proceeding:
retarget to the selected base when necessary (for example `gh pr edit <PR> --base <base>`),
verify actual PR state again and inspect the diff for inherited/duplicate changes.
Retargeting is not proof the commits are reconciled after a squash/rebase merge;
stop for an approved reconciliation if needed, then rerun checks/review for changed
code. Record not-yet-authorized push/PR actions as pending, not as completed.
Neither this workflow nor commit/push approval implies merge permission.

## Feature states

| State | Meaning |
| --- | --- |
| `pending` | No spec yet. The `spec-author` is the first actor. |
| `spec_ready` | Spec written. Waiting for human approval. Do not touch code. |
| `in_progress` | Scope approved. Test-generator/implementer cycle active. |
| `done` | Green checks, `reviewer` approved, the user reviewed the working tree, commits made and session closed. |
| `blocked` | Stuck. The reason lives in `progress/current.md` or `progress/spec_<name>.md`. |

A feature is SDD when `"sdd": true`. If the field is omitted, `sdd.default` in
`harness.config.json` applies (default `true`). Set `"sdd": false` only for work
that predates the harness or is genuinely trivial; record the reason in the
feature description. The harness source constitution explicitly authorizes
direct implementation with `sdd.default: false`; use approved acceptance, not a
fabricated spec. Target default remains `true`.

## The two human gates

The automatic flow stops **twice**:

1. **Before implementation:** when the `spec-author` finishes the three files,
   it sets the feature to `spec_ready` and stops. The human reads
   `specs/<NNN>_<name>/` and says "approved" (or requests changes). Only then
   does the `leader` transition `spec_ready → in_progress` and launch the
    `test-generator`, followed by the handoff protocol below and `implementer`.
2. **Before committing:** when the `reviewer` approves, the changes stay in the
   **working tree, uncommitted**. The human reviews them and gives explicit
   approval. The leader then launches `github-handler` for atomic commits, but
   never without that approval.

```text
pending → [spec-author] → spec_ready → ⏸ HUMAN → in_progress
        → [leader → test-generator → leader → implementer → reviewer]
        → ⏸ USER reviews → OK
        → [github-handler] atomic commits → done
```

## Test generation and handoff

Canonical ownership flow: `leader → test-generator → leader → implementer → reviewer`.
Only leader launches/resumes agents, sequentially. After human spec approval
(or approved acceptance for authorized `sdd: false` direct work), leader launches
test-generator BEFORE any production implementation, including each later cycle
that needs new tests. Test-generator never independently interviews the user.

Test-generator exclusively creates, modifies and deletes tests, fixtures,
snapshots, test assets, assertions and expected outputs. It runs meaningful RED
for missing required behavior, not syntax or environment failures, then writes
the full persistent contract to `progress/tests_<name>.md`. The contract includes:

- Feature and approved spec/scope; `R<n>` mapping for SDD or ordered approved
  acceptance mapping for direct work.
- Exact test paths/names/helpers, commands and working directory, coverage,
  expected failures and actual RED output/exit codes.
- Ownership inventory, including additions/deletions, and per-file SHA-256
  baselines for existing tests/assets in scope, not merely changes against HEAD.
- For docs-only work without behavior, explicitly approved and explained N/A
  instead of invented RED. Behavioral work always needs actual RED.

For SDD work the generator also writes `specs/<NNN>_<name>/tests.md`, one row
per requirement/task with the test(s) that prove it, refreshed on every
correction:

```markdown
| Requirement | Task | Test(s) |
| --- | --- | --- |
| R1 | T1 | `test_login_ok` (`tests/test_login.py`) |
```

Direct `sdd: false` work keeps this mapping in the handoff contract only.

If the approved scope lacks a requirement needed to write a test, or a gate is
still open (unapproved spec, unfinished predecessor review/user gate), the
generator stops instead of inventing or bypassing it:

- `REQUIREMENTS_MISSING -> progress/tests_<name>.md` — the leader uses the
  clarification path: clarify acceptance with the human, or amend the spec
  through `spec-author` and the human gate.
- `GATE_OPEN -> progress/tests_<name>.md` — the leader lists the gates to close,
  waits for them, then resumes the generator.

Neither marker reaches implementer; a partial contract is never forwarded.

Generator returns exactly:

```text
THIS IS THE TESTS -> progress/tests_<name>.md
```

Leader reads the ENTIRE artifact, validates meaningful RED and ownership
evidence, and forwards that exact marker PLUS the full unchanged contract to
implementer, never a lossy summary. The child may read the same complete artifact
at that exact path. Implementer records its SHA and test baselines, reproduces
RED before production edits, then makes only the minimum implementation to
GREEN and runs the full gate. Expected, contract-recorded feature RED after a
known-green pre-test gate is not an environment block; unexpected failures stop.

Implementer NEVER creates, edits or deletes tests/assets/expected outputs or the
handoff, even through shell or to repair a test. Missing/incorrect tests or new
coverage mean STOP: report `tests_requested` to leader, who resumes generator.
Implementation resumes only after refreshed tests, RED evidence and the full
persistent contract. Reviewer test rejections follow the same leader → generator
route; production defects return through leader to implementer. No unsupervised
agent-to-agent loops. Scope changes require a human-approved spec amendment (or
acceptance clarification for direct work), not invented requirements.

Reviewer checks requirement/acceptance traceability, RED-before-code and GREEN
evidence, and tests unchanged against the contract inventory/SHA baseline,
NOT HEAD (the checkout may already contain generator changes). Pending corrections
are reported, never silently applied. Leader may reflect completed generator
test-task checkboxes from its recorded evidence; implementer marks only its own
implementation tasks, not generator RED tasks. Generator does not edit specs.

Agent frontmatter allows/denies conventional test paths only. Tailor generator
allow rules and implementer deny rules for project-specific test locations;
ownership applies at every path. Shell is NOT sandboxed; these edit rules are not
complete mechanical protection. No new config/schema field is required.

## requirements.md — strict EARS

Each requirement is a numbered paragraph using one of these five patterns:

| Pattern | Template |
| --- | --- |
| **Ubiquitous** | `The system MUST <action>.` |
| **Event** | `WHEN <trigger>, the system MUST <action>.` |
| **State** | `WHILE <state>, the system MUST <action>.` |
| **Optional** | `WHERE <optional feature>, the system MUST <action>.` |
| **Unwanted** | `IF <unwanted event> THEN the system MUST <action>.` |

Hard rules:

- Every requirement has a stable id: `R1`, `R2`, …
- Every requirement MUST be verifiable by at least one concrete test, or by an
  explicitly approved and documented verification method (for example a
  migration check).
- Do not mix several `MUST` clauses in one requirement. Split it.
- Do not use weak verbs ("could", "may", "supports"). Use `MUST` / `MUST NOT`.
- Every criterion in the feature's `acceptance` list MUST be covered by at least
  one `R<n>`; close the file with the mapping table.

Example:

```markdown
## R1

WHEN the user runs `npm run ingest` with a new snapshot, the system MUST load
its records into the `silver` schema in one transaction.

## R2

IF the snapshot revision is older than the one already loaded THEN the system
MUST ignore it with a warning and exit with code 0.
```

## design.md — technical decisions

Capture **before** touching code:

- Which files are created or modified.
- Which new signatures appear (functions, classes, commands, endpoints).
- Which exceptions are reused or added.
- Which alternative was discarded and why (at least one).
- If the feature touches the data model: every source of truth that must stay in
  sync (for example ERD ↔ models ↔ migration), with the concrete change in each.
- If the feature touches a shared harness asset: what changes in `templates/`
  and how existing target installs are affected.

Lean on [`architecture.md`](architecture.md), [`conventions.md`](conventions.md)
and [`style.md`](style.md); `design.md` documents the points where the feature
touches the boundary of those rules.

## tasks.md — executable checklist

Discrete steps in order, each with a checkbox. Every task references at least
one `R<n>`.

```markdown
- [ ] T1 — Walking skeleton: generator RED for CLI → data → response, then
      leader handoff and implementer minimal GREEN. Covers: R1.
- [ ] T2 — Widen the same path: generator RED for older snapshots, then
      leader handoff and implementer minimal GREEN. Covers: R2.
- [ ] T3 — Final gate and traceability evidence. Covers: R1, R2.
```

Leader marks combined tasks `[x]` only after recorded generator RED and
implementer GREEN; implementer marks only separately assigned implementation
tasks. Generator-only tasks are reflected by leader from handoff evidence, not
claimed by implementer. The validator rejects
a `done` feature that still has an unchecked `[ ]`. If a task cannot be
completed, amend the spec (with reviewer and human approval) instead of leaving
the box open.

## Traceability (hard rule)

- Every test affected by the feature MUST map to an `R<n>` from its spec.
  Authorized direct work maps to approved acceptance instead; no spec is required.
- Every `R<n>` MUST have at least one concrete test or approved verification.
- The `reviewer` checks this correspondence explicitly and rejects if it is
  missing.
- The `implementer` documents the map in `progress/impl_<name>.md`:

```markdown
## Traceability
- R1 → `test_ingest_loads_snapshot`
- R2 → `test_ingest_ignores_older_revision`
```

## Changing an approved spec

- The spec is approved for implementation as written. If implementation reveals
  a missing requirement or a wrong design decision, **stop** and report.
- Do not silently invent requirements or design decisions. Propose an amendment
  to the spec; the human approves it; then continue.
- Record the amendment in `design.md` (decisions) and, if the acceptance list
  changes, in `feature_list.json`.

## When SDD does not apply

- Features with `"sdd": false`, including work that predates the harness.
- Trivial changes that do not reach feature level (typos, doc fixes): do them
  directly, without a spec.
- The process in this file is authoritative. Generic "spec-driven development"
  skills are orientation, not a replacement.
