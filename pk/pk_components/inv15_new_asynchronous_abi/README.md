# INV-15 - New asynchronous ABI

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The new asynchronous ABI is what lets a component wait without pinning anything. Instead of a pollable that only its own instance may look at, a call returns either a value or a subtask handle, and the host owns the readiness table. Because waiting is expressed as a handle rather than a blocked stack, a waiting component costs a table row instead of a thread.

## Responsibility

Own the asynchronous calling convention: subtask handles, the waitable-set primitive, cancellation propagation, and the guarantee that no guest stack is blocked while a call is outstanding.

## Owns

- Subtask handle allocation and lifetime
- Waitable sets and their readiness reporting
- Cancellation propagation from caller to subtask
- Backpressure when a component exceeds its outstanding-call budget
- The guarantee that waiting consumes no guest stack

## Explicitly does not own

- The interface definitions being called
- Stream and completion payload semantics
- Host I/O implementations
- Scheduling policy
- Language bindings

## Non-goals

- Implementing host I/O
- Choosing a scheduling policy
- Defining stream semantics
- Preserving the old pollable's instance-local shape

## Interfaces

- `call` - PK_ASYNC_CALL/1 - returns a value or a subtask handle
- `cancel` - PK_SUBTASK_CANCEL/1 - cancellation of an outstanding subtask
- `wait` - PK_WAITABLE_SET/1 - a set of subtask handles and their readiness

## Service-level objectives

- **no blocked stacks** - zero guest stacks blocked on an outstanding call (error budget: no budget)
- **cancellation** - p99 cancellation acknowledged within 1 scheduler tick (error budget: 1% may exceed)
- **wait cost** - a waiting component holds one table row and no thread (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-15 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-15 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-15`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-15`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
