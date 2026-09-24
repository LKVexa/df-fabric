# GAP-05 - State replication/consistency model

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The state replication and consistency model makes the edge's divergence explicit. Writes taken on both sides of a partition are kept, not silently lost: the model merges what commutes, and surfaces what genuinely conflicts for a decision instead of picking a winner by timestamp.

## Responsibility

Own replicated state semantics across sites: converge concurrent writes deterministically, detect genuine conflicts rather than resolving them by clock, and never discard a write without recording that it was discarded.

## Owns

- The replication consistency model and its convergence guarantee
- Version vectors and causal ordering
- Conflict detection and the conflict set
- Deterministic merge for commuting updates
- The record of every discarded write

## Explicitly does not own

- Transport between sites
- Storage engines
- Data residency policy
- Which sites replicate what
- Conflict resolution policy authorship

## Non-goals

- Providing linearizability across sites
- Choosing a winner by timestamp
- Transporting replication traffic
- Authoring resolution policy

## Interfaces

- `conflicts` - PK_CONFLICT_SET/1 - unresolved concurrent writes awaiting a decision
- `merge` - PK_MERGE_RESULT/1 - converged value or the conflict set
- `write` - PK_REPLICATED_WRITE/1 - a write with its originating site and version vector

## Service-level objectives

- **convergence** - identical write sets converge to an identical value regardless of order (error budget: no budget)
- **write preservation** - zero writes discarded without a recorded reason (error budget: no budget)
- **conflict detection** - 100% of causally concurrent writes reported as conflicts (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-05 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-05 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-05`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-05`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
