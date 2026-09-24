# INV-03 - Container hardening

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Container hardening is the list of things a container should not be allowed to do, checked before it runs: run as root, write to its own filesystem, keep Linux capabilities it never uses, run privileged, or skip a syscall filter. Each finding names the control that failed, and a workload only gets an exception if the exception is written down with an expiry date.

## Responsibility

Own the container hardening baseline: control definitions, pre-admission evaluation, named findings, and time-limited recorded exceptions.

## Owns

- The hardening control baseline
- Pre-admission evaluation
- Per-control findings
- Recorded, expiring exceptions
- Baseline versioning

## Explicitly does not own

- Image content scanning
- Runtime intrusion detection
- Kernel configuration
- Image building
- Authorization policy

## Non-goals

- Scanning image contents
- Detecting intrusions
- Tuning kernels

## Interfaces

- `baseline` - PK_HARDEN_BASELINE/1 - versioned control set
- `evaluate` - PK_HARDEN_EVAL/1 - spec to per-control findings
- `exception` - PK_HARDEN_EXCEPTION/1 - control, workload, reason, expiry

## Service-level objectives

- **baseline enforcement** - zero workloads admitted with an unexcepted failure (error budget: no budget)
- **exception hygiene** - zero exceptions honoured past expiry (error budget: no budget)
- **evaluation time** - p99 under 5ms per spec (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-03 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-03 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-03`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-03`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
