# SCH-01 - Workload Classification and Runtime Placement Engine

**Group:** 03_Multi_Runtime_Scheduler
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The multi-runtime scheduler is the piece Kubernetes does not have: it classifies a workload by trust, latency, and hardware need, then places it on a node that can actually honour that class. Classification and placement are separate steps, and a placement that would downgrade isolation is refused rather than made to fit.

## Responsibility

Own workload classification and runtime placement: derive a trust class, latency class, and hardware requirement for every workload, and bind it to a node whose attested tiers and capacity satisfy that class, or refuse placement with the unmet constraint named.

## Owns

- Workload classification (trust, latency, hardware)
- Candidate node filtering against hard constraints
- Scoring and deterministic tie-breaking
- Placement binding and its lease
- Refusal when no node satisfies the hard constraints

## Explicitly does not own

- Isolation enforcement on the node
- Capacity targets
- Node provisioning
- Application composition
- Data residency policy

## Non-goals

- Enforcing isolation
- Provisioning nodes
- Deciding instance counts
- Placing a workload on a node that cannot attest its required tier

## Interfaces

- `classify` - PK_WORKLOAD_CLASS/1 - trust, latency, and hardware classification
- `nodes` - PK_NODE_REPORT/1 - reported node capabilities, tiers, and free capacity
- `place` - PK_PLACEMENT/1 - placement request and its lease or refusal

## Service-level objectives

- **placement soundness** - zero placements onto a node lacking the required tier (error budget: no budget)
- **placement latency** - p99 decision under 100ms for 1,000 candidate nodes (error budget: 1% may exceed)
- **determinism** - identical inputs produce an identical placement (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run SCH-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate SCH-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run SCH-01`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate SCH-01`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
