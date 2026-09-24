# INV-14 - Previous asynchronous model

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The previous asynchronous model is the poll-based one: a component hands the host a list of pollables and blocks until one is ready. It works, it is simple, and it does not compose -- which is exactly why the new ABI exists. This element keeps it running honestly while it is still deployed, and states what it cannot do.

## Responsibility

Own the legacy poll-based async surface for components still using it: block on a pollable set with a bounded timeout, guarantee no lost readiness, and mark the model deprecated so nothing new is written against it.

## Owns

- The pollable set and its readiness semantics
- Bounded blocking with timeout
- Lost-wakeup prevention
- Deprecation status and migration reporting
- Refusal to compose a pollable across component boundaries

## Explicitly does not own

- The new asynchronous ABI
- Stream and future primitives
- Host I/O implementations
- Scheduling
- Placement

## Non-goals

- Composing async across components
- Being the model new code is written against
- Replacing the new ABI
- Unbounded blocking

## Interfaces

- `poll` - PK_POLL/1 - block on a pollable set with a timeout
- `pollable` - PK_POLLABLE/1 - a readiness handle owned by one instance

## Service-level objectives

- **no lost wakeups** - zero readiness signals dropped across a poll boundary (error budget: no budget)
- **bounded blocking** - zero polls blocking past their timeout (error budget: no budget)
- **migration visibility** - every use reports the deprecation and the migration target (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-14 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-14 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-14`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-14`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
