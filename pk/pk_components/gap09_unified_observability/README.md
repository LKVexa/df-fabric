# GAP-09 - Unified observability

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Unified observability is the estate's evidence layer. Every signal is attributed to the workload and tenant that produced it, signed by the node that reported it, and carries its own staleness -- so a missing signal reads as missing rather than as zero.

## Responsibility

Own signal ingestion and attribution: accept only signals signed by an attested reporter, attribute each to its tenant, site and workload, and expose staleness so absence is never mistaken for a healthy zero.

## Owns

- Signal ingestion and reporter authentication
- Tenant/site/workload attribution
- Staleness tracking per signal
- Cross-tenant query isolation
- The distinction between zero and absent

## Explicitly does not own

- What the signals mean to a consumer
- Alerting policy
- Long-term storage
- Node health decisions
- Capacity decisions

## Non-goals

- Deciding node health
- Alerting
- Long-term retention
- Inferring a value for a signal that was never reported

## Interfaces

- `catalogue` - PK_SIGNAL_CATALOGUE/1 - declared signals, their meaning and unit
- `query` - PK_SIGNAL_QUERY/1 - tenant-scoped read with staleness
- `submit` - PK_SIGNAL_SUBMISSION/1 - signed batch of signals from one reporter

## Service-level objectives

- **attribution** - zero signals stored without tenant, site and workload (error budget: no budget)
- **isolation** - zero queries returning another tenant's signals (error budget: no budget)
- **absence fidelity** - zero unreported signals returned as a numeric zero (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-09 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-09 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-09`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-09`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
