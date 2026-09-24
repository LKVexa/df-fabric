# INV-20 - HTTP component worlds

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

An HTTP component world is the smallest useful thing a serverless component can be: a world that imports an outgoing-request capability and exports an incoming-request handler, with both bodies as streams and trailers as completions. Because the world is explicit, a component that was never granted outgoing HTTP simply cannot make a call.

## Responsibility

Own the HTTP world definition and its enforcement: the handler export, the outgoing capability import, body streaming, trailer completion, and refusal of any egress the world did not grant.

## Owns

- The incoming-handler export shape
- The outgoing-request capability import
- Request and response bodies as streams
- Trailers as completions
- Egress allow-listing per world

## Explicitly does not own

- TLS termination
- Routing between components
- Transport implementation
- Business logic
- Placement

## Non-goals

- Implementing TLS
- Routing
- Owning the HTTP transport
- Buffering whole bodies in memory

## Interfaces

- `body` - PK_HTTP_BODY/1 - a request or response body as a stream
- `handler` - PK_HTTP_HANDLER/1 - the exported incoming-request function
- `outgoing` - PK_HTTP_OUTGOING/1 - the imported egress capability

## Service-level objectives

- **egress containment** - zero requests to hosts outside the world's allow-list (error budget: no budget)
- **streaming** - no body fully buffered before forwarding (error budget: no budget)
- **handler latency** - p99 handler dispatch under 1ms excluding user code (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-20 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-20 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-20`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-20`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
