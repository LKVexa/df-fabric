# INV-33 - Virtualization controller

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The virtualization controller is the node-local authority that turns a placement into a running guest and back again. It holds the lease: a guest exists because a lease says so, and when the lease expires without renewal the guest is reclaimed rather than orphaned.

## Responsibility

Own guest lifecycle against a renewable lease: admit a placement, start the guest, require lease renewal to keep it, and reclaim guests whose lease expired so no instance outlives the authority that created it.

## Owns

- The guest lease and its renewal
- Guest start, stop and reclaim
- Reconciliation between intended and actual guests
- Orphan detection and reclamation
- Refusal to start without a valid lease

## Explicitly does not own

- Placement decisions
- Isolation tier internals
- Resource adjustment
- Node lifecycle
- Capacity targets

## Non-goals

- Deciding placement
- Implementing runtimes
- Adjusting resources
- Keeping a guest alive past its lease because it looks healthy

## Interfaces

- `lease` - PK_GUEST_LEASE/1 - grant and renew the authority for one guest
- `reconcile` - PK_GUEST_RECONCILIATION/1 - intended versus actual, with actions taken

## Service-level objectives

- **no orphans** - zero guests running without a current lease after a reconcile pass (error budget: no budget)
- **lease enforcement** - zero guests started without a valid lease (error budget: no budget)
- **reconcile latency** - p99 reconcile pass under 200ms for 500 guests (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-33 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-33 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-33`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-33`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
