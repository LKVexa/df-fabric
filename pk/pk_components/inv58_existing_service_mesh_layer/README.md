# INV-58 - Existing service-mesh layer

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The existing service-mesh layer is already doing mTLS, retries and routing for current workloads, and the new runtime has to coexist with it rather than duplicate it. The sharpest hazard is retry multiplication: three app retries through a mesh that also retries three times is nine attempts against a struggling service. This element owns the division of labour.

## Responsibility

Own coexistence with the incumbent mesh: which layer retries, total-attempt budgets, identity handoff from mesh certificates to runtime identities, and detection of traffic bypassing the mesh.

## Owns

- Retry ownership between app runtime and mesh
- Total-attempt budgets
- Mesh-to-runtime identity mapping
- Mesh-bypass detection
- Migration of policies off the mesh

## Explicitly does not own

- The mesh's data plane
- Certificate issuance
- Application retry code
- Routing policy content
- Network hardware

## Non-goals

- Running the mesh
- Issuing certificates
- Writing app retry code

## Interfaces

- `bypass` - PK_MESH_BYPASS/1 - a flow observed outside the mesh
- `identity` - PK_MESH_IDENTITY/1 - certificate SAN to runtime identity
- `reconcile` - PK_MESH_RECONCILE/1 - effective retry ownership per route

## Service-level objectives

- **bounded attempts** - no call exceeds its total-attempt budget (error budget: no budget)
- **no bypass** - every bypass flow flagged within one scrape (error budget: no budget)
- **handoff cost** - p99 identity mapping under 100us (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-58 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-58 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-58`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-58`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
