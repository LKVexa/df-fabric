# INV-39 - Process sandbox tier

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The process sandbox tier is seccomp, namespaces and a dropped capability set: cheap, fast, and sharing a kernel with everything else on the box. It is the right tier for trusted code and the wrong one for anything hostile, so this element states the residual kernel attack surface instead of quietly calling itself isolation.

## Responsibility

Own the process-level sandbox: apply a default-deny syscall filter, drop all ambient capabilities, enter every namespace the profile requires, and report the residual kernel attack surface rather than presenting this tier as equivalent to a VM.

## Owns

- The seccomp syscall allow-list per profile
- Capability dropping
- Namespace entry and its completeness
- Residual kernel attack-surface reporting
- Refusal to start with an incomplete profile

## Explicitly does not own

- The kernel
- Hardware isolation
- Other tiers
- Container image formats
- Placement

## Non-goals

- Claiming VM-equivalent isolation
- Protecting against kernel bugs
- Running untrusted or hostile code
- Namespace-only confinement without seccomp

## Interfaces

- `apply` - PK_SANDBOX_APPLIED/1 - the verified applied state and residual surface
- `profile` - PK_SANDBOX_PROFILE/1 - syscalls, capabilities and namespaces

## Service-level objectives

- **default deny** - zero processes started without an applied default-deny filter (error budget: no budget)
- **capability drop** - zero processes retaining an unpermitted capability (error budget: no budget)
- **surface budget** - allow-lists at or below the declared syscall budget (error budget: breaches are reported, not blocked)

## Running it

```
python -m pk_core list
python -m pk_core run INV-39 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-39 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-39`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-39`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
