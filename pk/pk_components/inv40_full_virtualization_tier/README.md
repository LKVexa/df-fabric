# INV-40 - Full virtualization tier

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The full virtualization tier is the heavyweight end: a complete machine with its own kernel and a full device model. It is the tier you use when the workload is hostile or the guest OS is not yours, and it costs seconds to boot and hundreds of megabytes to run -- numbers this element states plainly so the tier is chosen on purpose rather than by default.

## Responsibility

Own full-machine virtualization: run a complete guest with its own kernel and full device model, enforce the strongest available isolation boundary, and account honestly for the boot time and memory footprint the tier costs.

## Owns

- Full guest lifecycle with a complete device model
- The strongest-available isolation boundary for a guest
- Boot-time and footprint accounting
- Guest-OS opacity (no host introspection assumptions)
- Refusal to run without the hardware primitive

## Explicitly does not own

- Guest operating systems
- The CPU primitive itself
- Placement
- Capacity targets
- MicroVM device minimalism

## Non-goals

- Minimal device models
- Millisecond boots
- Introspecting the guest OS
- Providing a software fallback when the hardware primitive is missing

## Interfaces

- `boot` - PK_FULL_VM_BOOT/1 - boot result with elapsed time and resident footprint
- `create` - PK_FULL_VM/1 - create a full guest with its device model and footprint

## Service-level objectives

- **primitive requirement** - zero guests started without the hardware primitive (error budget: no budget)
- **tenant exclusivity** - zero devices shared between guests of different tenants (error budget: no budget)
- **footprint honesty** - 100% of guests accounted at their real resident size (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-40 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-40 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-40`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-40`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
