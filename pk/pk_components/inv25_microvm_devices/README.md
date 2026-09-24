# INV-25 - MicroVM devices

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

MicroVM devices is where the minimal device model is actually defined and defended. Each device is paravirtual, declares the exact guest-visible surface it exposes, and carries a rationale -- because a device without a reason to exist is attack surface with a justification attached after the fact.

## Responsibility

Own the paravirtual device catalogue: define every permitted device, its guest-visible surface and its rationale, and refuse to register a device that emulates legacy hardware or exposes host resources directly.

## Owns

- The paravirtual device catalogue and its schema
- Guest-visible surface per device
- Rationale and review status for each device
- Refusal of legacy emulation
- Device surface diffing between model versions

## Explicitly does not own

- Device backend implementations
- MicroVM lifecycle
- The I/O datapath
- Guest drivers
- Snapshot serialization

## Non-goals

- Implementing device backends
- Writing guest drivers
- Emulating legacy PCI or ISA hardware
- Deciding which devices a workload gets

## Interfaces

- `catalogue` - PK_DEVICE_CATALOGUE/1 - permitted devices with surface and rationale
- `diff` - PK_DEVICE_SURFACE_DIFF/1 - what changed between two device versions

## Service-level objectives

- **review coverage** - 100% of catalogue entries carry a rationale and reviewer (error budget: no budget)
- **legacy exclusion** - zero legacy-emulation devices in the catalogue (error budget: no budget)
- **surface visibility** - every version change produces a surface diff (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-25 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-25 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-25`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-25`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
