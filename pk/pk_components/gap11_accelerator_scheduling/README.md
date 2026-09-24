# GAP-11 - Accelerator scheduling

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Accelerator scheduling treats a GPU or NPU as an exclusive, attestable resource rather than a divisible number. A device is either wholly assigned, partitioned into declared slices, or not available -- and a device is scrubbed between tenants before it is handed on.

## Responsibility

Own accelerator allocation: assign whole devices or declared partitions exclusively, never oversubscribe across tenants, and require a completed scrub before a device moves between tenants.

## Owns

- Accelerator inventory and partition topology
- Exclusive allocation and release
- Cross-tenant scrub enforcement
- Refusal to oversubscribe
- Accelerator capability matching (memory, generation, features)

## Explicitly does not own

- Device drivers and firmware
- Thermal ceilings
- Workload placement
- Hardware capability probing
- Model or kernel execution

## Non-goals

- Executing kernels
- Managing drivers
- Sharing a device across tenants
- Inventing partitions a device does not declare

## Interfaces

- `allocate` - PK_ACCELERATOR_ALLOCATION/1 - request and lease an accelerator
- `inventory` - PK_ACCELERATOR_INVENTORY/1 - devices, partitions and their features
- `scrub` - PK_SCRUB/1 - scrub state and completion evidence

## Service-level objectives

- **exclusivity** - zero devices concurrently allocated to two tenants (error budget: no budget)
- **scrub** - zero cross-tenant handovers without completed scrub evidence (error budget: no budget)
- **allocation latency** - p99 allocation decision under 10ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-11 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-11 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-11`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-11`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
