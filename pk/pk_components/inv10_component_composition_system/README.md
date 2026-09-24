# INV-10 - Component composition system

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The component composition system is what makes modules into something you can actually wire together: each component states its imports and exports as typed interfaces, and composition is linking them. A composition either closes -- every import satisfied by some export -- or it is not a composition at all.

## Responsibility

Own component linking: satisfy every import from a declared export or refuse the composition, detect dependency cycles, and produce a closed, content-addressed composition whose external imports are exactly what remains unsatisfied.

## Owns

- Component import/export declaration
- Link resolution across a composition
- Cycle detection
- Closure computation and the remaining external imports
- Content-addressed composition identity

## Explicitly does not own

- Module validation
- Interface type checking
- Runtime instantiation
- Host function implementations
- Placement

## Non-goals

- Validating modules
- Checking interface type compatibility in depth
- Instantiating at run time
- Leaving an import to be resolved by luck at run time

## Interfaces

- `component` - PK_COMPONENT/1 - a component with typed imports and exports
- `compose` - PK_COMPOSITION/1 - a closed composition and its external imports

## Service-level objectives

- **closure** - zero compositions published with an unsatisfied internal import (error budget: no budget)
- **determinism** - identical component sets produce an identical composition id (error budget: no budget)
- **link latency** - p99 under 200ms for 200-component compositions (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-10 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-10 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-10`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-10`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
