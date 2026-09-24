# INV-26 - MicroVM snapshotting

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

MicroVM snapshotting is what turns a hundred-millisecond cold boot into a few milliseconds, and it is also the easiest way to leak one tenant's memory into another's process. This element treats a snapshot as tenant-bound, entropy-poisoned material: restoring one into a different tenant is refused, and every restored guest is re-seeded.

## Responsibility

Own snapshot capture and restore: bind every snapshot to its originating tenant and device model, refuse a cross-tenant or model-mismatched restore, and re-seed guest entropy on every restore so clones do not share randomness.

## Owns

- Snapshot capture and its metadata
- Tenant binding of snapshot material
- Device-model compatibility checking on restore
- Entropy re-seeding after restore
- Restore-time budget and its measurement

## Explicitly does not own

- MicroVM lifecycle
- Device definitions
- Storage of snapshot blobs
- Guest application state semantics
- Placement

## Non-goals

- Live migration
- Cross-tenant template sharing
- Storing snapshot blobs
- Guaranteeing application-level correctness after restore

## Interfaces

- `capture` - PK_SNAPSHOT/1 - capture an instance with its tenant and model fingerprint
- `restore` - PK_SNAPSHOT_RESTORE/1 - restore result with elapsed time and re-seed proof

## Service-level objectives

- **tenant binding** - zero cross-tenant restores (error budget: no budget)
- **entropy** - zero restores without a re-seed (error budget: no budget)
- **restore time** - p99 restore under 10ms, an order faster than cold boot (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-26 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-26 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-26`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-26`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
