# INV-66 - Enterprise Wasm control plane

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The enterprise Wasm control plane sits above many lattices and many teams. It adds what a single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry never reaches a deployment manager.

## Responsibility

Own multi-lattice governance: organisation and lattice RBAC, admission guardrails on manifests, approved registries and signers, and an append-only change audit.

## Owns

- Organisation and lattice RBAC
- Manifest admission guardrails
- Approved registries and signers
- Change audit trail
- Cross-lattice inventory

## Explicitly does not own

- Lattice runtime
- Reconciliation
- Signing keys
- Identity provider
- Billing

## Non-goals

- Running lattices
- Holding signing keys
- Issuing identity

## Interfaces

- `admit` - PK_ECP_ADMIT/1 - manifest admission decision
- `audit` - PK_ECP_AUDIT/1 - append-only change record
- `rbac` - PK_ECP_RBAC/1 - role bindings per lattice

## Service-level objectives

- **guardrails** - zero unadmitted manifests forwarded (error budget: no budget)
- **audit integrity** - audit chain verifies end to end (error budget: no budget)
- **admission latency** - p99 under 50ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-66 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-66 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-66`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-66`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
