# GAP-01 - Edge Node Supervisor

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The edge node supervisor is the single local authority on a node: it owns the node's lifecycle state machine, drains workloads before the node stops accepting them, and keeps the node honest when the control plane is unreachable. Nothing else on the node may declare it healthy.

## Responsibility

Own the node lifecycle state machine -- joining, ready, draining, cordoned, stopped -- enforce legal transitions, and drain admitted workloads before a node leaves service.

## Owns

- The node lifecycle state machine and its legal transitions
- Local health aggregation for the node
- Workload drain ordering and completion
- Cordon and uncordon
- Local supervision when the control plane is unreachable

## Explicitly does not own

- Placement decisions
- Isolation enforcement
- Hardware capability discovery
- Control-plane membership
- Workload business logic

## Non-goals

- Deciding where drained workloads go
- Provisioning or decommissioning hardware
- Acting as a control-plane member
- Declaring a node healthy on missing evidence

## Interfaces

- `drain` - PK_DRAIN/1 - drain progress per workload with deadlines
- `health` - PK_NODE_HEALTH/1 - aggregated local health and its contributing signals
- `lifecycle` - PK_NODE_LIFECYCLE/1 - transition requests and the resulting node state

## Service-level objectives

- **transition legality** - zero illegal lifecycle transitions applied (error budget: no budget)
- **drain completeness** - zero nodes reporting stopped with resident workloads (error budget: no budget)
- **cordon latency** - placements stop within one scheduling interval of cordon (error budget: 1% may see one extra placement)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-01`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-01`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
