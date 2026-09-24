# GAP-14 - Data-gravity manager

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The data-gravity manager decides whether the computation moves to the data or the data moves to the computation. It costs both directions honestly against residency and egress, and it will recommend neither rather than propose a move that residency forbids.

## Responsibility

Own the move-compute-or-move-data decision: cost both directions against size, locality and egress, eliminate options residency forbids, and recommend the cheaper legal option or none at all.

## Owns

- Dataset location and size accounting
- Cost model for moving data versus moving compute
- Residency-legal option filtering
- The gravity recommendation and its reasoning
- Refusal when no legal option exists

## Explicitly does not own

- Executing the move
- Residency policy authorship
- Transport
- Placement decisions
- Storage engines

## Non-goals

- Executing moves
- Authoring residency policy
- Overriding a legal pin
- Placing compute directly

## Interfaces

- `cost` - PK_MOVE_COST/1 - per-direction cost breakdown
- `datasets` - PK_DATASET/1 - dataset location, size and classification
- `recommend` - PK_GRAVITY_RECOMMENDATION/1 - move-data, move-compute, or none, with cost

## Service-level objectives

- **legality** - zero recommendations violating residency (error budget: no budget)
- **completeness** - every recommendation carries a full cost breakdown (error budget: no budget)
- **decision latency** - p99 recommendation under 50ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-14 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-14 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-14`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-14`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
