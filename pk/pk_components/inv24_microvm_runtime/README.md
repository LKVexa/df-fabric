# INV-24 - MicroVM runtime

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The microVM runtime is the Firecracker-shaped tier: a stripped VMM with a minimal device model that boots in milliseconds. Its whole value is that the attack surface is small and the boot is fast, so this element refuses a configuration that widens the one or destroys the other.

## Responsibility

Own microVM instance lifecycle: boot a guest with only the declared minimal device set, enforce the boot-time budget, and refuse any configuration that adds a device outside the permitted minimal model.

## Owns

- MicroVM instance lifecycle (create, boot, pause, stop)
- The permitted minimal device model
- Boot-time budget enforcement
- Per-instance resource limits
- Refusal of out-of-model device requests

## Explicitly does not own

- The CPU virtualization primitive
- Device backend implementations
- Snapshot format
- Placement
- Guest operating systems

## Non-goals

- Full device emulation
- Live migration
- Running an unmodified general-purpose VM image
- Adding devices to satisfy a guest that wants them

## Interfaces

- `boot` - PK_MICROVM_BOOT/1 - boot result with elapsed time against the budget
- `create` - PK_MICROVM/1 - create an instance with its device set and limits
- `lifecycle` - PK_MICROVM_LIFECYCLE/1 - pause, resume, stop

## Service-level objectives

- **device model** - zero instances booted with an out-of-model device (error budget: no budget)
- **boot time** - p99 cold boot under the declared budget (error budget: 1% may exceed and are reported)
- **tenant isolation** - zero instances reused across tenants without destruction (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-24 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-24 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-24`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-24`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
