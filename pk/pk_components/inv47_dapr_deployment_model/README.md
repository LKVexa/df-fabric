# INV-47 - Dapr deployment model

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The deployment model decides where the application runtime lives relative to the application: a sidecar beside each instance, one shared agent per node, or embedded in-process. Each trades isolation against density, and the model's job is to make that trade explicit, give every application exactly one reachable runtime, and keep the runtime within a supported version of its control plane.

## Responsibility

Own runtime placement relative to applications: mode selection, one-runtime-per-instance binding, control-plane version-skew bounds, and the isolation consequences of each mode.

## Owns

- Deployment mode selection (sidecar, per-node, embedded)
- Binding each app instance to exactly one runtime
- Version-skew bounds against the control plane
- Mode-specific isolation guarantees
- Runtime lifecycle tied to the application's

## Explicitly does not own

- Building-block behaviour
- Scheduling of application instances
- Networking
- Image build
- Authorization

## Non-goals

- Implementing building blocks
- Scheduling instances
- Building images

## Interfaces

- `bind` - PK_DEPLOY_BIND/1 - instance-to-runtime binding
- `mode` - PK_DEPLOY_MODE/1 - sidecar, per-node or embedded
- `skew` - PK_DEPLOY_SKEW/1 - runtime and control-plane versions

## Service-level objectives

- **binding** - every ready instance has exactly one runtime (error budget: no budget)
- **skew** - zero runtimes more than one minor version behind (error budget: no budget)
- **startup** - p99 runtime ready within 500ms of instance start (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-47 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-47 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-47`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-47`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
