# GAP-03 - Topology-aware scheduler

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The topology-aware scheduler supplies what a flat scheduler cannot: locality cost and fair share. It scores candidates by how far they are from the data and the caller, and it refuses to let one tenant's demand crowd out another's floor.

## Responsibility

Own topology cost and fair-share scoring for placement: rank candidate nodes by locality distance and enforce each tenant's reserved share so no tenant is starved by a noisier neighbour.

## Owns

- The topology graph and its distance metric
- Locality cost scoring
- Per-tenant fair-share reservations
- Starvation detection and the fairness guard
- Anti-affinity spreading across failure domains

## Explicitly does not own

- Hard constraint filtering
- Trust classification
- Capacity targets
- Node lifecycle
- Data residency policy

## Non-goals

- Hard constraint filtering
- Owning the placement decision
- Provisioning capacity to satisfy a share
- Guaranteeing a share that was never reserved

## Interfaces

- `cost` - PK_LOCALITY_COST/1 - distance between two topology nodes
- `fairness` - PK_FAIR_SHARE/1 - reserved shares and the starvation verdict
- `topology` - PK_TOPOLOGY/1 - the region/site/rack graph and its edges

## Service-level objectives

- **share enforcement** - zero placements spending another tenant's reserved share (error budget: no budget)
- **cost determinism** - identical topology and candidates produce identical costs (error budget: no budget)
- **scoring latency** - p99 scoring under 20ms for 1,000 candidates (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-03 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-03 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-03`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-03`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
