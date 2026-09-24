# INV-42 - Capability descriptors

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Capability descriptors are what a reference becomes when it has to leave the process: a typed, serialized handle passed across an ABI boundary. Serialization is exactly where authority usually leaks, so this element makes a descriptor useless outside the table it belongs to.

## Responsibility

Own descriptor tables and the serialized form of a capability: bind every descriptor to its owning table, keep numbering non-reusable within a session, and refuse any descriptor presented to a table that did not issue it.

## Owns

- Per-process descriptor tables
- Descriptor allocation and closure
- Table binding of every descriptor
- Non-reuse of descriptor numbers within a session
- Typed transfer of descriptors across a boundary

## Explicitly does not own

- The underlying resources
- In-process reference semantics
- Wire protocols
- Policy authorship
- Placement

## Non-goals

- Implementing resources
- Cross-process number portability
- Reusing numbers for compactness
- Trusting a descriptor number on its own

## Interfaces

- `close` - PK_DESCRIPTOR_CLOSE/1 - permanently close a descriptor number
- `open` - PK_DESCRIPTOR/1 - allocate a typed descriptor in a table
- `resolve` - PK_DESCRIPTOR_RESOLVE/1 - resolve a descriptor within its own table

## Service-level objectives

- **table binding** - zero descriptors resolved in a table that did not issue them (error budget: no budget)
- **non-reuse** - zero descriptor numbers reused within a session (error budget: no budget)
- **type fidelity** - zero descriptors resolved as the wrong type (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-42 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-42 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-42`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-42`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
