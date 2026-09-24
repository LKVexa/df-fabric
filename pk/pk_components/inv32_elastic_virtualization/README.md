# INV-32 - Elastic virtualization

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Elastic virtualization is memory and vCPU that move while the guest is running -- ballooning, hot-plug, free-page reporting. It is how an edge node runs more than it has, and it is also how a node gets OOM-killed, so every adjustment here is bounded and reversible.

## Responsibility

Own live resource adjustment for running guests: grow and shrink guest memory and vCPUs within declared floors and ceilings, never reclaim below a guest's working-set floor, and refuse an adjustment that would oversubscribe the host past its reserve.

## Owns

- Live memory reclaim and growth per guest
- vCPU hot-plug within declared bounds
- The host reserve that is never allocated
- Guest working-set floors
- Refusal of oversubscription past the reserve

## Explicitly does not own

- Capacity targets
- Placement
- Guest applications
- The hypervisor's allocator
- Thermal ceilings

## Non-goals

- Deciding capacity targets
- Placing guests
- Guaranteeing a guest cooperates
- Overcommitting past the host reserve

## Interfaces

- `adjust` - PK_RESOURCE_ADJUSTMENT/1 - request a memory or vCPU change for a guest
- `host` - PK_HOST_RESOURCES/1 - total, reserved, allocated and free

## Service-level objectives

- **reserve** - zero allocations into the host reserve (error budget: no budget)
- **floors** - zero guests reclaimed below their working-set floor (error budget: no budget)
- **reversibility** - 100% of applied adjustments reversible to the previous value (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-32 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-32 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-32`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-32`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
