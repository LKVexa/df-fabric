# GAP-04 - Disconnected-operation controller

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The disconnected-operation controller is what lets an edge site keep working when the control plane is gone. It grants a bounded autonomy lease, narrows what the site may decide for itself as the partition lengthens, and reconciles honestly on reconnect instead of pretending nothing happened.

## Responsibility

Own site behaviour during control-plane partition: issue and expire bounded autonomy leases, degrade local decision authority as the partition lengthens, and produce a reconciliation record on reconnect.

## Owns

- Autonomy leases and their expiry
- Degradation tiers as a partition lengthens
- Local decision authority during partition
- The reconnection reconciliation record
- Cached policy and its staleness bound

## Explicitly does not own

- Transport or NAT traversal
- State replication semantics
- Policy authorship
- Node lifecycle
- Capability grants

## Non-goals

- Guaranteeing correctness of decisions made on stale policy
- Replacing the control plane
- Replicating state
- Maintaining connectivity

## Interfaces

- `lease` - PK_AUTONOMY_LEASE/1 - grant, renew, and expire a site's autonomy
- `reconcile` - PK_RECONCILIATION_RECORD/1 - decisions taken during the partition
- `tier` - PK_DEGRADATION_TIER/1 - what the site may decide right now

## Service-level objectives

- **lease enforcement** - zero decisions taken under an expired lease (error budget: no budget)
- **record completeness** - every local decision appears in the reconciliation record (error budget: no budget)
- **tier correctness** - zero decisions permitted above the current degradation tier (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-04 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-04 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-04`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-04`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
