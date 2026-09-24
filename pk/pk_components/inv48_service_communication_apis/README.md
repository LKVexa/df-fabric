# INV-48 - Service communication APIs

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Service communication APIs are how one application calls another by name: resolve the name, carry the caller's identity, apply a timeout, and retry only when the operation is safe to repeat. The discipline is in the retry -- a non-idempotent call retried after a timeout can charge a card twice, so retries are keyed and deduplicated at the callee.

## Responsibility

Own service-to-service invocation: name resolution, identity propagation, timeouts, idempotency-keyed retries with backoff, and callee-side deduplication.

## Owns

- Service name resolution
- Caller identity propagation
- Per-call timeouts
- Idempotency-keyed retries with bounded backoff
- Callee-side deduplication

## Explicitly does not own

- Transport encryption
- Authorization decisions
- Service discovery registries
- Business semantics
- Load balancing policy

## Non-goals

- Encrypting transport
- Deciding authorization
- Running a registry

## Interfaces

- `invoke` - PK_SVC_INVOKE/1 - a named call with identity and idempotency key
- `policy` - PK_SVC_RESILIENCY/1 - timeout, retry and backoff
- `resolve` - PK_SVC_RESOLVE/1 - logical name to endpoint

## Service-level objectives

- **exactly-once effects** - zero keyed operations executed twice (error budget: no budget)
- **bounded retries** - no call retried more than its policy allows (error budget: no budget)
- **latency** - p99 invocation overhead under 2ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-48 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-48 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-48`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-48`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
