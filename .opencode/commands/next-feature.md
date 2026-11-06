---
description: Start the next pending feature through the SDD flow (spec first)
agent: leader
---

Implement the next pending feature following the SDD flow in `AGENTS.md` and
`.agents/specs.md`.

- Resume the sole `in_progress` feature first; otherwise select by ascending id.
  Apply `.agents/specs.md#epics-and-stacked-prs` before generating files: same
  `initiative` means one sequential epic, blocked predecessors are not skipped,
  review/user gates finish before successors, but PR merge need not. The leader
  directs safe branch preparation through `github-handler` only after the user
  authorizes that branch operation; never generate later specs in parallel.
- If an SDD feature is `pending`: launch the `spec-author` and stop so the human
  can approve the spec.
- If the feature is `spec_ready`: do not touch code. Remind the human to review
  `specs/<NNN>_<name>/` and say "approved".
- After spec approval, or approved acceptance for authorized `sdd: false` direct
  work, run test-generator BEFORE implementer. No source spec is needed for the
  constitution's direct-work exception; target SDD default stays true.
- Require `THIS IS THE TESTS -> progress/tests_<name>.md`. Read and forward the
  entire unchanged persistent contract plus exact marker, not a summary. Validate
  meaningful RED, coverage/commands and ownership/SHA baselines before implementer.
- Resume an authorized `in_progress` task cycle from its evidence; without a
  valid contract run generator first. Ask before resuming if not authorized.
- Test corrections/new coverage, including reviewer rejection, go sequentially
  through leader → test-generator → leader → implementer with refreshed full
  contract/RED. Production defects go to implementer; no other role edits tests.
