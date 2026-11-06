# Tasks — {{FEATURE_NAME}}

Each behavioral task cycles test-generator RED → leader full contract handoff →
implementer minimal GREEN. For SDD features the generator also maintains
`specs/<NNN>_<name>/tests.md`, the requirement/task → tests table. T1 is one
walking skeleton from entry point to data to response through declared layers,
minimal and possibly stubbed; later tasks widen it, not horizontal layer
batches. Leader marks combined tasks `[x]` only from generator RED and
implementer GREEN evidence; implementer marks only separate implementation
subtasks, never claims generator test work.

- [ ] T1 — Walking skeleton: test-generator writes failing end-to-end test and
      `progress/tests_<name>.md`; leader forwards exact marker/full contract;
      implementer reproduces RED and changes only production to GREEN. Covers: R1.
- [ ] T2 — Widen same path: test-generator extends coverage, records RED and
      refreshes full contract through leader; implementer minimal GREEN. Covers: R1, R2.
- [ ] T3 — Docs, migration or generated production artifact. Covers: R2.
- [ ] T4 — Final gate `./init.sh`, traceability and unchanged test SHA baselines.
      Covers: R1–R3.
