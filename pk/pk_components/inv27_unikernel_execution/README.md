# INV-27 - Unikernel execution

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Unikernel execution is the single-address-space bet: the application and its kernel are linked into one image with no shell, no second process and no syscall surface to abuse. The isolation argument only holds if the image really is sealed, so this element verifies the seal rather than assuming it.

## Responsibility

Own unikernel image admission and execution: verify that an image is genuinely single-address-space and sealed -- no multi-process support, no dynamic loading, a closed syscall set -- and refuse to run one that is not.

## Owns

- Unikernel image seal verification
- The permitted syscall set per image
- Single-address-space enforcement
- Refusal of dynamically-linked or multi-process images
- Image entry-point and boot contract

## Explicitly does not own

- Building unikernel images
- The hypervisor beneath
- Language runtimes
- Device models
- Placement

## Non-goals

- Building images
- Providing a shell or debugger inside the guest
- Supporting multi-process workloads
- Trusting a metadata claim of sealing

## Interfaces

- `admit` - PK_UNIKERNEL_IMAGE/1 - submit an image with its seal manifest
- `run` - PK_UNIKERNEL_INSTANCE/1 - a running instance and its verified seal

## Service-level objectives

- **seal soundness** - zero images executed without a verified seal (error budget: no budget)
- **syscall fidelity** - zero images running with syscalls outside their verified set (error budget: no budget)
- **admission latency** - p99 verification under 100ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-27 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-27 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-27`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-27`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
