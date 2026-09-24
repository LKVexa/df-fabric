# GAP-15 - Runtime compatibility certification

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Runtime compatibility certification answers the question a heterogeneous edge estate asks constantly: will this artifact actually run on that node? It certifies against a declared matrix and refuses to guess, because an untested pair is not a supported pair.

## Responsibility

Own the runtime compatibility matrix: certify an artifact against a runtime and node profile from tested evidence only, and return uncertified -- never a guess -- for a pair that has not been tested.

## Owns

- The compatibility matrix and its versioning
- Certification verdicts and their evidence
- The distinction between incompatible and untested
- Certification expiry
- Deprecation and end-of-life signalling for runtime versions

## Explicitly does not own

- Running the compatibility tests
- Building artifacts
- Rollout sequencing
- Node capability probing
- Runtime implementations

## Non-goals

- Running the tests
- Fixing incompatibilities
- Sequencing rollouts
- Guessing at an untested pair

## Interfaces

- `certify` - PK_CERTIFICATION/1 - verdict for one artifact/runtime/profile triple
- `lifecycle` - PK_RUNTIME_LIFECYCLE/1 - supported, deprecated and end-of-life versions
- `matrix` - PK_COMPATIBILITY_MATRIX/1 - the tested triples and their results

## Service-level objectives

- **no inference** - zero certified verdicts without a recorded test result (error budget: no budget)
- **expiry** - zero expired certifications treated as current (error budget: no budget)
- **eol enforcement** - zero rollouts certified onto an end-of-life runtime (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-15 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-15 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-15`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-15`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
