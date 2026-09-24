# INV-11 - Interface contract language

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The interface contract language is WIT: the typed vocabulary that says what crosses a component boundary. It is the only thing standing between two components written in different languages and a memory-safety incident, so compatibility here is structural and checked, never assumed from a version number.

## Responsibility

Own interface type definitions and compatibility: decide whether two versions of an interface can be linked by comparing their structure, and classify every change as compatible, breaking, or additive.

## Owns

- Interface type definitions and their structure
- Structural compatibility checking
- Change classification (additive, compatible, breaking)
- Version semantics for interfaces
- Refusal to link structurally incompatible interfaces

## Explicitly does not own

- Bindings generation
- Component linking
- Runtime marshalling
- Language-specific type mapping
- Placement

## Non-goals

- Generating language bindings
- Linking components
- Marshalling values at run time
- Inferring compatibility from a version string

## Interfaces

- `compare` - PK_INTERFACE_DIFF/1 - change class between two interface versions
- `define` - PK_INTERFACE/1 - a typed interface definition

## Service-level objectives

- **compatibility soundness** - zero links permitted between structurally incompatible interfaces (error budget: no budget)
- **classification accuracy** - every change classified before publication (error budget: no budget)
- **comparison latency** - p99 under 5ms per interface pair (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-11 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-11 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-11`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-11`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
