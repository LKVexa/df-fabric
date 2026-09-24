# INV-59 - Application authorization

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Application authorization answers one question per call: may this identity perform this operation on this resource? The answer defaults to no, an explicit deny beats any allow, and every decision -- including the reason -- is recorded so a refusal can be explained and an allow can be audited.

## Responsibility

Own call-level authorization: default-deny policy evaluation, deny precedence, operation and resource matching, and an explained, auditable decision record.

## Owns

- Policy evaluation
- Default deny
- Deny precedence over allow
- Operation and resource pattern matching
- Decision records with reasons

## Explicitly does not own

- Identity issuance
- Policy authoring UX
- Transport security
- Secret storage
- Business rules

## Non-goals

- Issuing identity
- Authoring policy
- Securing transport

## Interfaces

- `decide` - PK_AUTHZ_DECIDE/1 - identity, operation, resource to decision
- `policy` - PK_AUTHZ_POLICY/1 - versioned allow and deny rules
- `record` - PK_AUTHZ_RECORD/1 - decision, reason, policy version

## Service-level objectives

- **default deny** - zero allows without a matching rule (error budget: no budget)
- **explainability** - every decision carries a reason (error budget: no budget)
- **decision latency** - p99 under 200us (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-59 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-59 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-59`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-59`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
