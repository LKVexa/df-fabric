# INV-34 - Legacy CPU expansion path

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The legacy CPU expansion path is the unglamorous truth of edge estates: hardware from several generations runs side by side, and a workload built for the newest instruction set will fault on the oldest node. This element defines the baseline everything must run on and makes any step above it an explicit, checked requirement.

## Responsibility

Own the CPU baseline and feature-level policy: define the instruction-set baseline every workload must run on, gate any workload requiring features above it to nodes that actually have them, and never present a higher level to a guest than the host provides.

## Owns

- The instruction-set baseline for the estate
- Feature-level definitions above the baseline
- Workload-to-node feature matching
- The guest-visible feature mask
- Refusal to expose a feature the host lacks

## Explicitly does not own

- CPU procurement
- Compiler flags
- Placement decisions
- Microcode updates
- Performance tuning

## Non-goals

- Emulating missing instructions
- Choosing hardware
- Presenting a feature the host lacks
- Assuming a homogeneous fleet

## Interfaces

- `baseline` - PK_CPU_BASELINE/1 - the estate baseline and the levels above it
- `mask` - PK_CPU_MASK/1 - the guest-visible feature set for an instance
- `match` - PK_CPU_MATCH/1 - whether a node satisfies a workload's level

## Service-level objectives

- **placement soundness** - zero workloads placed on a node below their feature level (error budget: no budget)
- **mask honesty** - zero guests shown a feature the host does not provide (error budget: no budget)
- **baseline coverage** - 100% of the fleet meets the estate baseline (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-34 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-34 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-34`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-34`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
