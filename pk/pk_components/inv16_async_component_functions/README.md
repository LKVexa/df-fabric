# INV-16 - Async component functions

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Async component functions are the guest-visible shape of the new ABI: a function declared async in the interface may return before its work is finished, and the caller decides whether to wait. The hard part is composition -- a sync caller of an async callee must still be correct, and re-entrancy must not corrupt the callee's state.

## Responsibility

Own the guest-facing async function surface: declaration, the sync/async call matrix, re-entrancy rules and the state machine each async function is compiled into.

## Owns

- Async function declaration and lifting
- The sync-caller/async-callee bridging rules
- Re-entrancy admission for an in-flight instance
- Per-call state machine storage
- Return-value delivery on completion

## Explicitly does not own

- Subtask handle mechanics
- Stream and completion payloads
- Scheduling
- Host I/O
- Interface syntax

## Non-goals

- Inferring async-ness at run time
- Owning the subtask table
- Making every function async
- Sharing state between in-flight calls

## Interfaces

- `declare` - PK_ASYNC_DECL/1 - build-time async-ness of a function
- `invoke` - PK_ASYNC_INVOKE/1 - a call carrying its own state machine
- `reentrancy` - PK_REENTRANCY/1 - admission decision for a re-entrant call

## Service-level objectives

- **state isolation** - zero bytes of call state shared between in-flight calls (error budget: no budget)
- **exactly once** - every completed call delivers its value exactly once (error budget: no budget)
- **bridge cost** - p99 sync-caller bridging under 5us (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-16 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-16 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-16`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-16`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
