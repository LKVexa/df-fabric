# INV-29 - Hybrid Wasm/unikernel

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The hybrid Wasm/unikernel model puts a Wasm runtime inside a unikernel image: the module gets the component model's portability and the unikernel's hardware-backed boundary at once. The point is defence in depth, so this element refuses a composition where one layer's guarantees silently substitute for the other's.

## Responsibility

Own the composition of a Wasm runtime inside a unikernel image: verify that both layers are independently sound, that the Wasm module's imports are a subset of what the unikernel actually exposes, and refuse a composition relying on only one layer.

## Owns

- Composition of a Wasm module with a unikernel host image
- Import/export reconciliation across the two layers
- Independent verification of each layer
- Defence-in-depth invariant enforcement
- Refusal when a layer is degraded to a pass-through

## Explicitly does not own

- The Wasm runtime implementation
- Unikernel toolchains
- Module compilation
- The hypervisor
- Placement

## Non-goals

- Implementing the Wasm runtime
- Building unikernel images
- Treating one strong layer as equivalent to two
- Satisfying module imports from the host kernel

## Interfaces

- `compose` - PK_HYBRID_COMPOSITION/1 - compose a module with a host image
- `verify` - PK_HYBRID_VERIFICATION/1 - per-layer verification results

## Service-level objectives

- **layer count** - zero compositions admitted with fewer layers than the environment requires (error budget: no budget)
- **import closure** - zero modules admitted with an unsatisfied import (error budget: no budget)
- **verification independence** - both layers verified separately for every composition (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-29 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-29 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-29`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-29`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
