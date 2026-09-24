# INV-57 - Durable execution

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Durable execution makes a long-running workflow survive crashes by recording what happened rather than where the code was. Each activity's result goes into a history; after a crash the workflow code re-runs from the top and every completed activity returns its recorded result instead of running again. That only works if the workflow code is deterministic, so divergence from the history is detected and refused.

## Responsibility

Own durable workflows: event-sourced history, deterministic replay, once-only activity effects, and detection of non-deterministic workflow code.

## Owns

- The workflow history
- Deterministic replay
- Once-only activity execution
- Non-determinism detection
- Resumption after crash

## Explicitly does not own

- Activity business logic
- History storage backend
- Timers infrastructure
- Scheduling of workers
- Messaging

## Non-goals

- Writing activities
- Storing history
- Scheduling workers

## Interfaces

- `activity` - PK_WF_ACTIVITY/1 - a recorded unit of work
- `history` - PK_WF_HISTORY/1 - ordered activity events
- `replay` - PK_WF_REPLAY/1 - deterministic re-execution against history

## Service-level objectives

- **once-only effects** - zero activities executed twice across replays (error budget: no budget)
- **determinism** - every divergence detected before effects (error budget: no budget)
- **replay speed** - p99 replay of 1000 events under 100ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-57 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-57 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-57`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-57`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
