# INV-23 - Hardware virtualization primitive

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The hardware virtualization primitive is the floor everything above it stands on: the CPU's own trap-and-emulate machinery. It is either present and usable or it is not, and no amount of software above it can manufacture it, so this element reports it honestly and refuses to pretend nested virtualization is the same thing as bare metal.

## Responsibility

Own detection and gating of the CPU virtualization extensions: report whether VT-x/AMD-V, EPT/NPT, and nested virtualization are actually usable on this host, and refuse to advertise a primitive that is present in CPUID but disabled or already claimed.

## Owns

- Detection of CPU virtualization extensions
- The usable-versus-present distinction
- Nested-virtualization depth reporting
- Exclusivity of the KVM-equivalent device
- Refusal when the primitive is claimed by another hypervisor

## Explicitly does not own

- The VMM itself
- Guest lifecycle
- Device emulation
- Isolation policy
- Scheduling

## Non-goals

- Implementing a VMM
- Enabling the extension in firmware
- Emulating virtualization in software
- Reporting nested as equivalent to bare metal

## Interfaces

- `claim` - PK_VIRT_CLAIM/1 - exclusive claim on the virtualization device
- `probe` - PK_VIRT_PRIMITIVE/1 - detect and report the virtualization primitive

## Service-level objectives

- **report soundness** - zero hosts reporting the primitive usable when the device cannot be opened (error budget: no budget)
- **nesting honesty** - zero nested hosts reporting depth 0 (error budget: no budget)
- **probe latency** - p99 probe under 50ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-23 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-23 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-23`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-23`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
