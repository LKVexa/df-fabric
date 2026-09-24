# INV-65 - Capability providers

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Capability providers are the long-lived processes that give components access to the outside world -- a key-value store, an HTTP server, a message broker -- behind a contract id. One provider serves many links, so the rule that matters is isolation between them: each link has its own configuration and credentials, and one component cannot see or use another's.

## Responsibility

Own provider lifecycle and link isolation: contract identity, per-link configuration, health checking, and restart without losing link state.

## Owns

- Provider contract identity
- Per-link configuration and credentials
- Link isolation
- Provider health checks
- Restart with link-state restoration

## Explicitly does not own

- Component logic
- The backing services
- Link authorization policy
- Artifact signing
- Scheduling providers

## Non-goals

- Implementing backends
- Authorizing links
- Scheduling

## Interfaces

- `contract` - PK_PROVIDER_CONTRACT/1 - contract id the provider implements
- `health` - PK_PROVIDER_HEALTH/1 - provider health status
- `link` - PK_PROVIDER_LINK/1 - component, link name, config

## Service-level objectives

- **isolation** - zero calls served with another link's configuration (error budget: no budget)
- **restart continuity** - every link restored after restart (error budget: no budget)
- **call overhead** - p99 provider dispatch under 1ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-65 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-65 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-65`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-65`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
