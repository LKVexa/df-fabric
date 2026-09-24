# INV-54 - Broker implementations

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Broker implementations are the concrete engines behind the messaging contract. Two ship here: a fan-out broker that copies each message to every subscriber, and a partitioned log that keeps per-key order and lets consumers replay from an offset. They make opposite trade-offs, and the contract is only portable if both pass the same checks.

## Responsibility

Own the reference brokers: fan-out and partitioned-log implementations, per-key ordering, consumer offsets and replay, and contract conformance of each.

## Owns

- The fan-out broker
- The partitioned-log broker
- Per-key ordering by partition
- Consumer offsets and replay
- Broker conformance against the messaging contract

## Explicitly does not own

- The messaging contract
- Delivery guarantees policy
- Cluster operation
- Schemas
- Transport

## Non-goals

- Defining the contract
- Running a cluster
- Owning schemas

## Interfaces

- `fanout` - PK_BROKER_FANOUT/1 - copy-to-all delivery
- `log` - PK_BROKER_LOG/1 - partitioned, offset-addressed log
- `offset` - PK_BROKER_OFFSET/1 - a consumer's committed position

## Service-level objectives

- **ordering** - zero per-key reorderings in the log broker (error budget: no budget)
- **fan-out completeness** - every subscriber receives every message (error budget: no budget)
- **append latency** - p99 append under 2ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-54 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-54 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-54`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-54`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
