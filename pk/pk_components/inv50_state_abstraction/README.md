# INV-50 - State abstraction

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The state abstraction is a key/value contract with the concurrency rules written down: every value carries an etag, a write that names a stale etag is refused, and keys are namespaced by application so two apps sharing a store cannot read each other's data by picking the same key.

## Responsibility

Own the state contract: namespaced keys, etag-based optimistic concurrency, first-write and last-write modes, bulk operations and the consistency guarantees each mode gives.

## Owns

- Key namespacing per application
- Etag optimistic concurrency
- Concurrency mode selection
- Bulk get and set semantics
- The contract every state store must meet

## Explicitly does not own

- Store implementations
- Replication between sites
- Encryption at rest
- Query languages
- Backups

## Non-goals

- Implementing stores
- Replicating across sites
- Encrypting at rest

## Interfaces

- `bulk` - PK_STATE_BULK/1 - atomic multi-key write
- `get` - PK_STATE_GET/1 - value and etag
- `set` - PK_STATE_SET/1 - write with optional etag

## Service-level objectives

- **no lost updates** - zero stale-etag writes accepted in first-write mode (error budget: no budget)
- **isolation** - zero reads across application namespaces (error budget: no budget)
- **latency** - p99 single-key operation overhead under 1ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-50 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-50 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-50`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-50`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
