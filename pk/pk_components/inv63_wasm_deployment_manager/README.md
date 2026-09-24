# INV-63 - Wasm deployment manager

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The Wasm deployment manager holds desired state -- which components, how many, spread across which labels -- and reconciles the lattice toward it. Its guarantees are convergence (repeated reconciliation reaches the desired state and then does nothing) and safe rollout (never more than the allowed number of instances unavailable while a version changes).

## Responsibility

Own declarative deployment: desired-state storage, reconciliation diffs, spread constraints, idempotent convergence and bounded-unavailability rollouts.

## Owns

- Desired-state storage
- Reconciliation diff computation
- Spread across host labels
- Idempotent convergence
- Rolling updates with a max-unavailable bound

## Explicitly does not own

- The application manifest format
- Running components
- Artifact signing
- Host provisioning
- Provider implementations

## Non-goals

- Defining manifests
- Running components
- Provisioning hosts

## Interfaces

- `desired` - PK_DEPLOY_DESIRED/1 - component, version, count, spread
- `diff` - PK_DEPLOY_DIFF/1 - start and stop actions
- `rollout` - PK_DEPLOY_ROLLOUT/1 - batched update plan

## Service-level objectives

- **convergence** - a second reconcile after convergence emits zero actions (error budget: no budget)
- **availability** - never more than max-unavailable instances down in rollout (error budget: no budget)
- **reconcile time** - p99 diff under 10ms for 1000 instances (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-63 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-63 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-63`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-63`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
