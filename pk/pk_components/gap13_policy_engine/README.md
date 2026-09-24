# GAP-13 - Policy engine

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The policy engine is where the estate's rules are evaluated rather than scattered. Decisions default to deny, the most specific matching rule wins with deterministic tie-breaking, and every verdict carries the rule that produced it -- so an operator can always answer why.

## Responsibility

Own policy evaluation for the estate: evaluate a request against versioned rules, default to deny, and return an explainable verdict naming the deciding rule and the policy version it came from.

## Owns

- Rule representation and specificity ordering
- Deny-by-default evaluation
- Deterministic tie-breaking between equally specific rules
- Verdict explanation
- Policy versioning and staleness

## Explicitly does not own

- Policy authorship
- Enforcement at the call site
- Identity or attestation
- Signing the policy bundle
- What a caller does with a verdict

## Non-goals

- Authoring rules
- Enforcing verdicts
- Widening a tenant's authority
- Evaluating against an unverified bundle

## Interfaces

- `evaluate` - PK_POLICY_VERDICT/1 - allow or deny with the deciding rule
- `explain` - PK_POLICY_EXPLANATION/1 - every rule that matched and why one won
- `load` - PK_POLICY_BUNDLE/1 - a signed, versioned rule set

## Service-level objectives

- **deny by default** - zero requests allowed without a matching allow rule (error budget: no budget)
- **determinism** - identical request and bundle produce an identical verdict (error budget: no budget)
- **explainability** - 100% of verdicts name their deciding rule and policy version (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-13 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-13 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-13`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-13`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
