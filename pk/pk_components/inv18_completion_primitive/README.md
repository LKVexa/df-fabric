# INV-18 - Completion primitive

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The completion primitive is the one-shot counterpart to a stream: exactly one value, delivered once, to exactly one receiver. Having it as its own type rather than a stream of length one means the compiler knows there is no second value coming, so the receiver needs no loop and the writer cannot accidentally send twice.

## Responsibility

Own one-shot value delivery: a future handle that resolves at most once, an explicit error resolution, and the refusal of a second resolution or a second receiver.

## Owns

- Future handle allocation and typing
- At-most-once resolution
- Error resolution as a first-class outcome
- Single-receiver enforcement
- Abandonment detection when the writer is dropped unresolved

## Explicitly does not own

- Many-valued flow
- The subtask table
- Retry policy
- Transport
- Payload meaning

## Non-goals

- Carrying many values
- Retrying the producer
- Broadcasting to several receivers
- Allowing a resolution to be overwritten

## Interfaces

- `abandon` - PK_FUTURE_ABANDON/1 - writer dropped without resolving
- `future` - PK_FUTURE/1 - a typed one-shot handle
- `resolve` - PK_FUTURE_RESOLVE/1 - value or error resolution

## Service-level objectives

- **at most once** - zero futures resolved twice (error budget: no budget)
- **no orphans** - every abandoned future raises on the receiver (error budget: no budget)
- **resolution cost** - p99 resolution delivery under 1us within an instance (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-18 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-18 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-18`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-18`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
