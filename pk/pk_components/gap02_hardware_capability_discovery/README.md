# GAP-02 - Hardware capability discovery

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Hardware capability discovery is what makes the rest of the estate honest about heterogeneity. It reports only what it has actually probed, distinguishes a capability that is absent from one it could not test, and never lets a node advertise more than it proved.

## Responsibility

Probe and publish the node's real hardware capabilities -- isolation primitives, accelerators, instruction-set extensions, secure elements -- as a signed, timestamped report in which unprobed is never reported as present.

## Owns

- Capability probing and its result states
- The node capability report and its freshness
- Separation of absent from unprobed
- Re-probe scheduling
- Refusal to advertise unproven capability

## Explicitly does not own

- Scheduling or placement
- Attestation of node identity
- Tier admission
- Accelerator allocation
- Firmware or driver management

## Non-goals

- Making placement decisions
- Attesting node identity
- Installing drivers
- Inferring a capability from a sibling node

## Interfaces

- `probe` - PK_CAPABILITY_PROBE/1 - run and record one capability probe
- `report` - PK_NODE_CAPABILITIES/1 - the node's signed capability report with freshness
- `schedule` - PK_PROBE_SCHEDULE/1 - which probes run when

## Service-level objectives

- **report soundness** - zero capabilities reported present without a successful probe (error budget: no budget)
- **freshness** - 99% of consumed reports younger than the freshness bound (error budget: 1% may be refused as stale)
- **probe cost** - full probe sweep under 5s on a constrained edge node (error budget: 5% may exceed on first boot)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-02`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-02`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
