# INV-06 - Traditional IaC

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Traditional infrastructure-as-code works in two steps: plan what will change, then apply that plan against a recorded state. It goes wrong when the world moves between the two -- someone else applies, or the plan is old. So a plan is tied to the state serial it was made against and is refused if that has moved; drift is detected by comparing real resources with the state; and protected resources cannot be destroyed by a plan at all.

## Responsibility

Own plan and apply against recorded state: diffing, state serials, stale-plan refusal, drift detection and destroy protection.

## Owns

- Plan computation
- State serials and locking
- Stale-plan refusal
- Drift detection
- Destroy protection

## Explicitly does not own

- Cloud provider APIs
- Configuration language design
- Secrets
- CI pipelines
- GitOps sync

## Non-goals

- Calling provider APIs
- Designing configuration languages
- Running CI

## Interfaces

- `apply` - PK_IAC_APPLY/1 - apply a plan to state
- `drift` - PK_IAC_DRIFT/1 - differences between reality and state
- `plan` - PK_IAC_PLAN/1 - create, update, delete against a serial

## Service-level objectives

- **no stale applies** - zero plans applied against a moved serial (error budget: no budget)
- **protection** - zero protected resources destroyed by plan (error budget: no budget)
- **drift visibility** - drift detected within one scan interval (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-06`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-06`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
