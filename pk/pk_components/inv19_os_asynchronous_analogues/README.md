# INV-19 - OS asynchronous analogues

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

OS asynchronous analogues are the mapping between the component world's streams and futures and what the host operating system actually offers -- epoll, kqueue, io_uring, IOCP. Each has a different shape (readiness versus completion), and the mapping has to be honest about which, because a readiness API pretending to be a completion API loses errors.

## Responsibility

Own the host-side asynchronous backend: detect the available mechanism, map readiness or completion semantics onto stream credit and future resolution, and degrade to a portable fallback without changing observable behaviour.

## Owns

- Backend detection and selection
- Readiness-to-credit mapping
- Completion-to-future mapping
- The portable fallback backend
- Per-backend error translation into component-world errors

## Explicitly does not own

- Stream and future semantics
- The async ABI
- Guest code
- Scheduling policy
- Kernel behaviour

## Non-goals

- Reimplementing kernel interfaces
- Exposing backend detail to guests
- Choosing scheduling policy
- Pretending a readiness API reports completion errors

## Interfaces

- `arm` - PK_ASYNC_ARM/1 - arm a descriptor for readiness or submit a completion
- `backend` - PK_ASYNC_BACKEND/1 - the selected mechanism and its semantics class
- `reap` - PK_ASYNC_REAP/1 - collect readiness or completion events

## Service-level objectives

- **behavioural identity** - identical component-visible outcomes on every backend (error budget: no budget)
- **fallback availability** - the portable backend is available 100% of the time (error budget: no budget)
- **reap latency** - p99 event reaped within 1 scheduler tick of readiness (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-19 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-19 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-19`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-19`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
