# INV-17 - Streaming primitive

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The streaming primitive carries many values over time through one typed handle. What makes it worth having as a primitive rather than a convention is that backpressure, end-of-stream and the reader's disappearance are all part of the type -- a writer that ignores a closed reader gets an error, not a silently discarded value.

## Responsibility

Own the stream handle: typed element flow, credit-based backpressure, explicit end-of-stream, and the errors a dropped end produces on the other side.

## Owns

- Stream handle allocation and typing
- Credit-based backpressure between writer and reader
- Explicit end-of-stream signalling
- Dropped-end detection and error delivery
- Buffer bounds for a stream in flight

## Explicitly does not own

- One-shot value delivery
- The subtask table
- Transport encoding
- Scheduling of readers and writers
- Payload semantics

## Non-goals

- Unbounded buffering
- Inferring end-of-stream from a timeout
- Carrying one-shot values
- Defining what the elements mean

## Interfaces

- `close` - PK_STREAM_CLOSE/1 - explicit end-of-stream or drop
- `credit` - PK_STREAM_CREDIT/1 - credit granted by the reader
- `stream` - PK_STREAM/1 - a typed stream handle with reader and writer ends

## Service-level objectives

- **bounded memory** - in-flight buffer never exceeds granted credit (error budget: no budget)
- **drop detection** - a write after a drop errors on the first attempt (error budget: no budget)
- **element cost** - p99 element handoff under 1us within an instance (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-17 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-17 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-17`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-17`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
