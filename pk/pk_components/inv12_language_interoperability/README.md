# INV-12 - Language interoperability

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Language interoperability is the promise that a Rust component and a Go component can call each other without either one learning the other's memory layout. It works by never sharing memory at all: values are lowered into the canonical ABI on the way out and lifted on the way in, and a type a language cannot represent is a build error rather than a silent truncation.

## Responsibility

Own canonical lifting and lowering across the language boundary: map every interface type to each guest language's representation, refuse a mapping that would lose information, and guarantee no memory is shared between components.

## Owns

- Canonical ABI lifting and lowering
- Per-language type mapping tables
- Refusal of lossy mappings
- Ownership transfer semantics at the boundary
- The no-shared-memory guarantee between components

## Explicitly does not own

- Compilers and toolchains
- Interface definitions
- Composition linking
- Host function implementations
- Placement

## Non-goals

- Writing compilers
- Defining interfaces
- Sharing memory for performance
- Silently truncating a value to make a mapping work

## Interfaces

- `lift` - PK_CANONICAL_LIFT/1 - a canonical value lifted into a guest representation
- `lower` - PK_CANONICAL_LOWER/1 - a guest value lowered into the canonical ABI
- `mapping` - PK_TYPE_MAPPING/1 - per-language representation of an interface type

## Service-level objectives

- **no loss** - zero values silently truncated or re-encoded lossily (error budget: no budget)
- **no sharing** - zero bytes of linear memory shared between components (error budget: no budget)
- **boundary cost** - p99 lowering+lifting under 2us for scalar values (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-12 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-12 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-12`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-12`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
