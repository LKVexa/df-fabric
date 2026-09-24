# INV-28 - Unikernel implementations

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Unikernel implementations are the concrete toolchains -- MirageOS, Unikraft, OSv and the rest -- and they are not interchangeable. Each supports a different language, a different device set and a different maturity of security response. This element keeps that register honest instead of letting 'unikernel' stand in for a single thing.

## Responsibility

Own the register of supported unikernel toolchains: record each one's language support, maturity, security-response posture and known limitations, and refuse to select a toolchain for a workload whose requirements it does not actually meet.

## Owns

- The toolchain register and its attributes
- Language and runtime support per toolchain
- Maturity and security-response classification
- Toolchain selection for a workload
- Refusal when no registered toolchain fits

## Explicitly does not own

- Building images
- Seal verification
- The hypervisor
- Upstream toolchain development
- Placement

## Non-goals

- Developing toolchains upstream
- Building images
- Verifying image seals
- Treating all unikernels as equivalent

## Interfaces

- `register` - PK_TOOLCHAIN/1 - a supported unikernel toolchain and its attributes
- `select` - PK_TOOLCHAIN_SELECTION/1 - the chosen toolchain and the reason

## Service-level objectives

- **selection soundness** - zero selections of a toolchain missing a required capability (error budget: no budget)
- **production maturity** - zero experimental toolchains selected in production (error budget: no budget)
- **review freshness** - 100% of registered toolchains reviewed within the declared interval (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-28 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-28 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-28`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-28`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
