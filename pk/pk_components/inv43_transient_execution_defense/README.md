# INV-43 - Transient-execution defense

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Transient-execution defense is the tax every isolation boundary pays after Spectre. Mitigations are not free and not universal, so the honest position is a per-node record of which are active, what they cost, and which trust classes may not be co-located without them.

## Responsibility

Own transient-execution mitigation state: record which mitigations are active on each node with their measured cost, and refuse co-tenancy of mutually distrusting workloads on a node whose required mitigations are absent.

## Owns

- Per-node mitigation inventory and its status
- Measured cost of each active mitigation
- Co-tenancy rules derived from mitigation state
- Sibling-thread policy
- Refusal of co-location when required mitigations are missing

## Explicitly does not own

- Microcode
- Kernel mitigation implementation
- Placement decisions
- CPU procurement
- Isolation tiers

## Non-goals

- Implementing mitigations
- Applying microcode
- Claiming a mitigation the node does not report
- Deciding placement

## Interfaces

- `cotenancy` - PK_COTENANCY/1 - whether two workloads may share this node
- `status` - PK_MITIGATIONS/1 - active mitigations, status and measured cost

## Service-level objectives

- **co-tenancy** - zero cross-tenant co-locations without the required mitigations (error budget: no budget)
- **status honesty** - zero mitigations reported active without a read-back (error budget: no budget)
- **cost visibility** - 100% of active mitigations carry a measured cost (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-43 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-43 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-43`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-43`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
