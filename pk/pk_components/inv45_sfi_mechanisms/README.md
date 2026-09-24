# INV-45 - SFI mechanisms

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Software fault isolation is the fallback when hardware will not help: masking every memory access into a sandbox region so a compromised module cannot reach outside it. It is cheap and portable, and it is only as good as the guarantee that every access really was rewritten -- so this element verifies that rather than assuming it.

## Responsibility

Own software fault isolation: confine memory accesses to a sandbox region by masking, verify that every access in a module was actually rewritten, and refuse to load a module containing an unmasked access.

## Owns

- The sandbox region and its mask
- Access rewriting verification
- Indirect-branch target confinement
- Refusal of modules with unmasked accesses
- The measured overhead of masking

## Explicitly does not own

- Hardware capability enforcement
- Compilers
- The Wasm specification
- Other isolation tiers
- Placement

## Non-goals

- Replacing hardware capability enforcement where it exists
- Implementing a compiler
- Confining accesses that were never rewritten
- Claiming isolation from an unverified module

## Interfaces

- `load` - PK_SFI_MODULE/1 - load a module after verifying every access is masked
- `mask` - PK_SFI_MASK/1 - the region base, size and mask applied to accesses

## Service-level objectives

- **confinement** - zero accesses served outside the sandbox region (error budget: no budget)
- **verification** - 100% of loaded modules fully verified (error budget: no budget)
- **overhead** - masking overhead at or below 15% (error budget: measured and reported per module)

## Running it

```
python -m pk_core list
python -m pk_core run INV-45 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-45 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-45`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-45`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
