# INV-56 - Distributed stateful compute

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Distributed stateful compute is the virtual-actor model: an actor is addressed by id, activated on some host when first called, and processes one message at a time. The guarantees that make it useful are single activation -- never two live copies of the same actor -- and turn-based execution, so actor code needs no locks.

## Responsibility

Own virtual actors: placement and single activation, turn-based message processing, idle deactivation with state persistence, and reactivation elsewhere after host loss.

## Owns

- Actor placement table
- Single-activation guarantee
- Turn-based concurrency
- Idle deactivation and state persistence
- Reactivation after host failure

## Explicitly does not own

- State store implementation
- Actor business logic
- Host provisioning
- Network transport
- Scheduling of hosts

## Non-goals

- Implementing storage
- Writing actor logic
- Provisioning hosts

## Interfaces

- `call` - PK_ACTOR_CALL/1 - a message to an actor id
- `placement` - PK_ACTOR_PLACEMENT/1 - actor id to host
- `state` - PK_ACTOR_STATE/1 - persisted actor state

## Service-level objectives

- **single activation** - zero actors with two live activations (error budget: no budget)
- **turn isolation** - zero overlapping turns per actor (error budget: no budget)
- **activation latency** - p99 cold activation under 50ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-56 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-56 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-56`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-56`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
