# PLN-01 - Intent plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The intent plane holds the desired state of the estate as a live graph rather than as disconnected Terraform state and Kubernetes YAML. It accepts declarations, resolves them into a dependency-ordered reconciliation plan, and hands that plan to the planes below. It never executes: planning and execution are deliberately separated.

## Responsibility

Own the authoritative desired-state graph for the estate, admit or reject declarations against policy, and emit a dependency-ordered, dry-runnable reconciliation plan for downstream planes to execute.

## Owns

- The desired-state graph and its schema
- Declaration admission and validation
- Dependency resolution and plan ordering
- Drift detection against reported actual state
- Plan versioning, diffing, and rollback targets

## Explicitly does not own

- Execution of any plan step
- Workload placement decisions
- Runtime or node lifecycle
- Data-plane transport
- Secret material

## Non-goals

- Executing plan steps
- Acting as a general-purpose configuration database
- Reconciling state the estate does not declare
- Replacing GitOps as the change entry point

## Interfaces

- `declare` - PK_DECLARATION/1 - submit or retract a declaration
- `graph` - PK_INTENT_GRAPH/1 - read-only node and edge projection
- `plan` - PK_RECONCILIATION_PLAN/1 - dependency-ordered plan with dry-run results
- `report` - PK_ACTUAL_STATE/1 - reported actual state ingested for drift detection

## Service-level objectives

- **plan latency** - p99 plan emission under 2s for graphs up to 10k nodes (error budget: 0.5% of plans may exceed)
- **admission correctness** - zero admitted declarations violating policy (error budget: no budget: any breach is a blocker)
- **drift detection** - drift surfaced within one reconciliation interval of a report (error budget: 1% of reports may lag one interval)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-01`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-01`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
