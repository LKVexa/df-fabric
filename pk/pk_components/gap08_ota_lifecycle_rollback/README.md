# GAP-08 - OTA lifecycle/rollback

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

OTA lifecycle and rollback is how an edge estate survives its own updates. Every rollout is staged, every stage has a health gate, and the rollback target is pinned before the first node is touched -- so a bad update stops at the canary instead of reaching the fleet.

## Responsibility

Own the over-the-air update lifecycle: stage a signed bundle across waves, gate each wave on health, and roll back to the pinned previous version the moment a gate fails.

## Owns

- Rollout waves and their ordering
- Per-wave health gates
- The pinned rollback target
- Automatic rollback on gate failure
- Update bundle admission (signed only)

## Explicitly does not own

- Building update bundles
- Signing keys
- Node health measurement
- Node lifecycle transitions
- What the update contains

## Non-goals

- Building or signing bundles
- Measuring node health
- Guaranteeing a rollback succeeds on a bricked node
- Promoting between environments

## Interfaces

- `gate` - PK_ROLLOUT_GATE/1 - the health verdict for one wave
- `rollback` - PK_ROLLBACK/1 - revert to the pinned target
- `rollout` - PK_ROLLOUT/1 - start a staged rollout of a verified bundle

## Service-level objectives

- **blast radius** - a failing update reaches no more than the first wave before rollback (error budget: no budget)
- **rollback pinning** - zero rollouts started without a pinned rollback target (error budget: no budget)
- **gate honesty** - zero waves started while the previous gate was failing (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-08 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-08 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-08`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-08`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
