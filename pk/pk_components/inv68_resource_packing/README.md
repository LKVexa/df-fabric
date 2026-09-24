# INV-68 - Resource packing

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Resource packing decides how many workloads fit on how many hosts. Packing well means fewer hosts for the same work; packing carelessly means one dimension -- usually memory -- runs out while CPU sits idle. The packer places across every dimension at once, keeps a headroom reserve, and reports the fragmentation it leaves behind.

## Responsibility

Own multi-dimensional bin packing: first-fit-decreasing placement, headroom reservation, overcommit ratios by dimension and fragmentation reporting.

## Owns

- Multi-dimensional placement
- Headroom reservation
- Per-dimension overcommit ratios
- Fragmentation reporting
- Packing efficiency against a naive baseline

## Explicitly does not own

- Workload classification
- Host provisioning
- Thermal policy
- Accelerator matching
- Preemption

## Non-goals

- Classifying workloads
- Provisioning hosts
- Matching accelerators

## Interfaces

- `capacity` - PK_PACK_CAPACITY/1 - per-host, per-dimension capacity
- `fragmentation` - PK_PACK_FRAG/1 - stranded capacity report
- `pack` - PK_PACK/1 - workloads to host assignments

## Service-level objectives

- **no memory overcommit** - zero hosts with memory placed above capacity minus headroom (error budget: no budget)
- **efficiency** - hosts used within 10% of the lower bound (error budget: 5% of batches may exceed)
- **pack time** - p99 under 100ms for 1000 workloads (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-68 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-68 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-68`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-68`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
