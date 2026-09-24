# PLN-05 - Elasticity plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.

## Responsibility

Own capacity targets per workload: convert observed demand into a bounded, hysteretic scale decision including scale-to-zero, and never emit a target outside the declared floor and ceiling.

## Owns

- Capacity targets per workload
- Scale-up and scale-down hysteresis
- Scale-to-zero and cold-start admission
- Floor and ceiling enforcement
- Oscillation suppression

## Explicitly does not own

- Placement of new capacity
- Node provisioning
- Workload isolation
- The demand signal itself
- Cost accounting

## Non-goals

- Placing or provisioning capacity
- Deciding node count
- Guaranteeing cold-start latency
- Overriding an externally lowered ceiling

## Interfaces

- `limits` - PK_CAPACITY_LIMITS/1 - declared floor, ceiling, and hysteresis parameters
- `observe` - PK_DEMAND/1 - demand samples per workload
- `target` - PK_CAPACITY_TARGET/1 - emitted capacity target with the reason

## Service-level objectives

- **target bounds** - zero targets outside the declared floor/ceiling (error budget: no budget)
- **reaction time** - p95 scale-up decision within two demand samples of threshold breach (error budget: 5% may take a third sample)
- **stability** - no more than one direction change per workload per grace period (error budget: 1% of workloads may exceed under demand step changes)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-05 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-05 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-05`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-05`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
