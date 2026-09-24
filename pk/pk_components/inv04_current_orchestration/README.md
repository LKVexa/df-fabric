# INV-04 - Current orchestration

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Current orchestration is the scheduler the estate uses today: desired replica counts, reconciliation, and node drains for maintenance. The new platform has to coexist with it and eventually take over, so its behaviour is modelled exactly -- including the rule that a drain must never take a service below its disruption budget.

## Responsibility

Own the model of the incumbent orchestrator: replica reconciliation, node drain with disruption budgets, and the hand-off surface to the new scheduler.

## Owns

- Replica reconciliation model
- Node drain procedure
- Disruption budget enforcement
- Workload inventory for hand-off
- Behavioural parity checks against the new scheduler

## Explicitly does not own

- Cluster provisioning
- The API server
- Networking
- Image building
- New-platform scheduling

## Non-goals

- Provisioning clusters
- Running the API server
- Scheduling on the new platform

## Interfaces

- `drain` - PK_ORCH_DRAIN/1 - a budget-respecting node drain
- `inventory` - PK_ORCH_INVENTORY/1 - workloads for hand-off
- `reconcile` - PK_ORCH_RECONCILE/1 - desired versus running

## Service-level objectives

- **availability** - zero drains that breach a disruption budget (error budget: no budget)
- **convergence** - replicas match desired within 30s (error budget: 1% may exceed)
- **inventory completeness** - every running workload listed for hand-off (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-04 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-04 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-04`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-04`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
