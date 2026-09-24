# INV-08 - Dynamic infrastructure model

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The dynamic infrastructure model treats capacity as something borrowed, not owned: nodes join a pool on a lease, are reclaimed when the lease lapses, and the pool grows and shrinks between hard bounds as demand changes. Two things must never happen -- unbounded growth, and a node reclaimed while it is still running work.

## Responsibility

Own elastic capacity: lease-based node membership, demand-driven scaling within bounds, safe reclamation of idle nodes and cost accounting.

## Owns

- Leased node membership
- Demand-driven scale-out and scale-in
- Hard pool bounds
- Safe reclamation of idle nodes
- Cost accounting per pool

## Explicitly does not own

- Provider provisioning APIs
- Workload scheduling
- Image building
- Billing systems
- Networking

## Non-goals

- Provisioning hardware
- Scheduling work
- Billing

## Interfaces

- `cost` - PK_DYN_COST/1 - node-hours per pool
- `lease` - PK_DYN_LEASE/1 - node lease and expiry
- `scale` - PK_DYN_SCALE/1 - scaling decision

## Service-level objectives

- **bounded** - pool never exceeds its maximum (error budget: no budget)
- **safe reclaim** - zero busy nodes reclaimed (error budget: no budget)
- **responsiveness** - scale decision within one tick of demand change (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-08 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-08 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-08`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-08`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
