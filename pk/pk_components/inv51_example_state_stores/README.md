# INV-51 - Example state stores

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Example state stores are the proof that the state contract is implementable more than one way. Two stores ship here -- an in-memory map and a file-backed journal -- and both are run through one conformance suite, so 'implements the state contract' is a test result rather than a claim.

## Responsibility

Own the reference state stores and the conformance suite they, and any third-party store, must pass.

## Owns

- The in-memory reference store
- The file-backed journal store
- The shared conformance suite
- Durability behaviour of the file store across restart
- Reporting which contract checks a store passes

## Explicitly does not own

- The state contract itself
- Production database operation
- Replication
- Encryption at rest
- Adapter admission

## Non-goals

- Operating production databases
- Replicating
- Defining the contract

## Interfaces

- `conformance` - PK_STATE_CONFORMANCE/1 - the suite and its per-check results
- `store` - PK_STATE_STORE/1 - a reference store implementation

## Service-level objectives

- **conformance** - every shipped store passes every check (error budget: no budget)
- **durability** - file store loses zero acknowledged writes across restart (error budget: no budget)
- **suite time** - full conformance suite under 1s per store (error budget: none may exceed 5s)

## Running it

```
python -m pk_core list
python -m pk_core run INV-51 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-51 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-51`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-51`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
