# INV-01 - Legacy infrastructure substrate

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The legacy infrastructure substrate is everything that already runs: physical hosts and long-lived VMs, many past vendor support, some with nobody clearly responsible for them. Moving to a new platform starts with an honest inventory. This element compares what the records say with what was actually discovered, tracks end-of-life dates, and refuses to schedule a host for migration until every workload on it has an owner.

## Responsibility

Own the legacy estate inventory: discovered versus recorded hosts, end-of-life tracking, workload ownership and migration eligibility.

## Owns

- Discovered-host inventory
- Reconciliation against the system of record
- End-of-life tracking
- Workload ownership mapping
- Migration eligibility decisions

## Explicitly does not own

- Performing migrations
- Hardware procurement
- Workload re-platforming
- Network changes
- Decommissioning hardware

## Non-goals

- Migrating workloads
- Buying hardware
- Decommissioning

## Interfaces

- `eligibility` - PK_LEGACY_ELIGIBLE/1 - migration eligibility with reasons
- `inventory` - PK_LEGACY_INV/1 - discovered hosts and their workloads
- `reconcile` - PK_LEGACY_RECONCILE/1 - ghosts, strays and matches

## Service-level objectives

- **inventory accuracy** - every discovered host is either recorded or flagged as a stray (error budget: no budget)
- **safe migration** - zero hosts with unowned workloads scheduled to move (error budget: no budget)
- **freshness** - discovery re-run at least daily (error budget: one missed run per week)

## Running it

```
python -m pk_core list
python -m pk_core run INV-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-01`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-01`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
