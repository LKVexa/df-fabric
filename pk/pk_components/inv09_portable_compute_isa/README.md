# INV-09 - Portable compute ISA

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The portable compute ISA is the bytecode everything above it compiles to: a small, deterministic instruction set with no ambient environment and no undefined behaviour to exploit. Portability is only worth anything if the same module computes the same answer everywhere, so this element validates modules rather than trusting their headers.

## Responsibility

Own module validation and the deterministic execution profile: verify structure, types and the declared feature set before a module runs, and refuse any module using a non-deterministic or unapproved feature.

## Owns

- Module structural and type validation
- The approved feature set per profile
- Determinism profile enforcement
- Refusal of unvalidated or over-featured modules
- Module size and section limits

## Explicitly does not own

- Compilers producing modules
- Runtime hardening
- The component model above it
- Host function semantics
- Placement

## Non-goals

- Compiling source to bytecode
- Hardening the engine
- Running an unvalidated module
- Guaranteeing determinism for opted-out profiles

## Interfaces

- `profile` - PK_ISA_PROFILE/1 - permitted features and determinism class
- `validate` - PK_MODULE_VALIDATION/1 - validation verdict with the feature set actually used

## Service-level objectives

- **validation soundness** - zero modules executed without passing validation (error budget: no budget)
- **determinism** - identical modules and inputs produce identical results within a deterministic profile (error budget: no budget)
- **validation latency** - p99 under 20ms for modules up to 4MiB (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-09 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-09 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-09`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-09`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
