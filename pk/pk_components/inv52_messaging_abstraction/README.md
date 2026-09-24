# INV-52 - Messaging abstraction

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The messaging abstraction lets an application publish to a topic and subscribe to one without knowing the broker. Every message travels in one envelope -- id, source, type, time, data -- and subscriptions route by rule, with a dead-letter topic for what no rule or handler can take.

## Responsibility

Own the publish/subscribe contract: the message envelope, topic and subscription model, content-based routing rules and dead-letter routing.

## Owns

- The message envelope
- Topic and subscription model
- Content-based routing rules
- Dead-letter routing
- Topic-level access scoping

## Explicitly does not own

- Broker implementations
- Delivery guarantees and redelivery
- Message schemas
- Transport
- Consumer business logic

## Non-goals

- Implementing brokers
- Guaranteeing delivery
- Defining payload schemas

## Interfaces

- `envelope` - PK_MSG_ENVELOPE/1 - id, source, type, time, data
- `publish` - PK_MSG_PUBLISH/1 - an enveloped message to a topic
- `subscribe` - PK_MSG_SUBSCRIBE/1 - a routed subscription

## Service-level objectives

- **no silent drops** - every unroutable message reaches the dead-letter topic (error budget: no budget)
- **envelope completeness** - zero messages published without id and source (error budget: no budget)
- **publish latency** - p99 publish overhead under 1ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-52 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-52 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-52`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-52`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
