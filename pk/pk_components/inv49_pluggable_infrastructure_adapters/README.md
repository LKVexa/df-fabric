# INV-49 - Pluggable infrastructure adapters

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Pluggable infrastructure adapters are how a new database or broker joins the runtime without changing an application. The value is only real if the plug is checked: an adapter declares the contract and optional features it implements, and the loader verifies that declaration against the adapter itself before admitting it -- a claimed feature that is not there is refused at load, not discovered in production.

## Responsibility

Own adapter admission: contract declaration, method-level conformance checking, feature verification, version pinning and isolation of adapter failures from the runtime.

## Owns

- Adapter contract declarations
- Load-time conformance verification
- Optional-feature verification
- Adapter version pinning
- Containment of adapter faults

## Explicitly does not own

- The backing systems themselves
- Building-block semantics
- Application code
- Credentials
- Deployment

## Non-goals

- Implementing backends
- Defining contracts
- Holding credentials

## Interfaces

- `admit` - PK_ADAPTER_ADMIT/1 - the verified admission record
- `contract` - PK_ADAPTER_CONTRACT/1 - required and optional methods
- `declare` - PK_ADAPTER_DECL/1 - contract, version and features claimed

## Service-level objectives

- **honest admission** - zero adapters admitted with an unverified feature claim (error budget: no budget)
- **containment** - an adapter fault affects only its own component (error budget: no budget)
- **load time** - p99 admission check under 50ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-49 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-49 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-49`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-49`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
