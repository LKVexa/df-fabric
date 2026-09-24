# INV-07 - GitOps transition layer

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The GitOps transition layer makes a git repository the source of desired state: a controller applies whatever the approved branch says, reverts changes made behind its back, and reports them. It only follows commits signed by an allowed key, and rolling back means reverting a commit -- so every change to the estate has an author, a review and an undo.

## Responsibility

Own git-driven reconciliation: signed-commit verification, sync to the cluster, revert and report of out-of-band changes, and rollback by revert.

## Owns

- Signed-commit verification
- Sync from commit to live state
- Out-of-band change detection and revert
- Rollback by revert
- Sync history

## Explicitly does not own

- Git hosting
- Code review tooling
- The live control store
- Image building
- Secrets storage

## Non-goals

- Hosting git
- Running code review
- Building images

## Interfaces

- `drift` - PK_GITOPS_DRIFT/1 - out-of-band changes found
- `sync` - PK_GITOPS_SYNC/1 - commit to live state
- `verify` - PK_GITOPS_VERIFY/1 - commit signature check

## Service-level objectives

- **provenance** - zero unsigned commits applied (error budget: no budget)
- **convergence** - live state matches head within one sync interval (error budget: 1% may exceed)
- **drift reporting** - every reverted change reported (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-07 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-07 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-07`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-07`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
