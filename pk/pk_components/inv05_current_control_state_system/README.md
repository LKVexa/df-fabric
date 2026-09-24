# INV-05 - Current control-state system

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The current control-state system is the consistent key-value store every controller reads and writes: each change gets a revision number, updates are compare-and-swap, and controllers watch for changes from a revision onward. The trap is compaction -- a watcher that asks for history that has been discarded must be told so, not silently given a gap.

## Responsibility

Own the control-state model: revisioned keys, compare-and-swap transactions, watches from a revision, and compaction with explicit refusal of discarded history.

## Owns

- Global revision numbering
- Compare-and-swap transactions
- Watch from revision
- Compaction
- Refusal of watches from compacted revisions

## Explicitly does not own

- Consensus implementation
- Controller logic
- Backups
- Storage hardware
- Authorization

## Non-goals

- Implementing consensus
- Writing controllers
- Taking backups

## Interfaces

- `compact` - PK_CSTATE_COMPACT/1 - discard history below a revision
- `txn` - PK_CSTATE_TXN/1 - compare, then success or failure ops
- `watch` - PK_CSTATE_WATCH/1 - changes from a revision

## Service-level objectives

- **linearisable writes** - zero transactions applied with a failed compare (error budget: no budget)
- **no silent gaps** - every watch either receives all changes or is told they were compacted (error budget: no budget)
- **write latency** - p99 under 10ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-05 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-05 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-05`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-05`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
