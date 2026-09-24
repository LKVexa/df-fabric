# INV-53 - Message reliability

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Message reliability turns 'published' into 'processed'. Delivery is at-least-once: a message stays owned by the broker until the consumer acknowledges it, reappears if the consumer dies holding it, and after a bounded number of attempts is parked in a dead-letter queue instead of looping forever. Because redelivery happens, consumers deduplicate by message id.

## Responsibility

Own delivery guarantees: acknowledgement, visibility timeouts, redelivery, bounded attempts, dead-lettering of poison messages and consumer-side deduplication.

## Owns

- Acknowledgement protocol
- Visibility timeout and redelivery
- Maximum delivery attempts
- Poison-message dead-lettering
- Consumer idempotency by message id

## Explicitly does not own

- Routing rules
- The envelope
- Broker storage
- Business retry logic
- Ordering

## Non-goals

- Routing
- Storing messages
- Ordering

## Interfaces

- `ack` - PK_MSG_ACK/1 - acknowledgement
- `deliver` - PK_MSG_DELIVER/1 - a leased delivery
- `dlq` - PK_MSG_DLQ/1 - a dead-lettered message and its attempt history

## Service-level objectives

- **no loss** - zero unacknowledged messages lost (error budget: no budget)
- **bounded poison** - no message delivered more than its attempt cap (error budget: no budget)
- **redelivery delay** - p99 redelivery within timeout plus 1s (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-53 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-53 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-53`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-53`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
