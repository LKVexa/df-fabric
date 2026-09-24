# GAP-10 - Power/thermal-aware scheduling

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Power and thermal-aware scheduling is the constraint a data-centre scheduler never had to model. An edge node in a hot cabinet on a battery cannot run what a racked node can, and this element makes that a hard ceiling the scheduler cannot argue with.

## Responsibility

Own power and thermal ceilings per node: convert measured thermal and power state into a capacity ceiling and an exclusion verdict, and lower the ceiling before hardware throttling or shutdown does it unpredictably.

## Owns

- Thermal and power state per node
- Capacity ceiling derived from that state
- Node exclusion under thermal emergency
- Hysteresis on ceiling recovery
- Battery-budget awareness

## Explicitly does not own

- Placement decisions
- Capacity targets
- Hardware fan or governor control
- Node lifecycle
- Accelerator allocation

## Non-goals

- Controlling fans or CPU governors
- Making placement decisions
- Guaranteeing a node never throttles
- Exempting any workload from a ceiling

## Interfaces

- `ceiling` - PK_POWER_CEILING/1 - derived capacity ceiling and exclusion verdict
- `policy` - PK_THERMAL_POLICY/1 - thresholds and hysteresis per environment
- `thermal` - PK_THERMAL_STATE/1 - measured temperature, power draw and battery state

## Service-level objectives

- **emergency exclusion** - zero placements onto a node above its emergency threshold (error budget: no budget)
- **pre-emption** - ceiling lowered before hardware throttling in 99% of thermal ramps (error budget: 1% may be overtaken by hardware)
- **stability** - no more than one exclusion flip per node per hysteresis window (error budget: 1% may exceed under sensor noise)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-10 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-10 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-10`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-10`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
