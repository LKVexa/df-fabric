# INV-31 - Function execution architecture

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The function execution architecture is the request-scoped end of the spectrum: an invocation gets an instance, does one job, and the instance is either recycled within its tenant or destroyed. Everything hard about it is the reuse decision, so that is what this element owns.

## Responsibility

Own function-instance lifecycle around a single invocation: decide warm reuse versus cold start under a strict same-tenant-same-version rule, bound concurrency per instance, and destroy instances rather than leaking state between invocations.

## Owns

- Function instance pool and its reuse rule
- Warm-versus-cold decision
- Per-instance concurrency bound
- Invocation-scoped state clearing
- Instance eviction and maximum age

## Explicitly does not own

- The isolation tier beneath
- Capacity targets
- Routing or load balancing
- Function source code
- Placement

## Non-goals

- Cross-tenant instance sharing
- Routing invocations
- Guaranteeing warm starts
- Persisting state between invocations

## Interfaces

- `invoke` - PK_INVOCATION/1 - run one invocation, cold or warm
- `pool` - PK_FUNCTION_POOL/1 - instances, their tenant, version and age

## Service-level objectives

- **tenant isolation** - zero instances reused across tenants (error budget: no budget)
- **version fidelity** - zero invocations served by an instance on a different code version (error budget: no budget)
- **warm rate** - at least 80% warm invocations in steady state (error budget: 20% may be cold)

## Running it

```
python -m pk_core list
python -m pk_core run INV-31 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-31 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-31`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-31`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
