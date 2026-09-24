# INV-46 - Distributed application runtime

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

A distributed application runtime gives an application its infrastructure as named building blocks -- state, pub/sub, secrets, invocation -- reached through one local API. The application never learns which database or broker sits behind a name, and a component is only reachable by the applications it is scoped to.

## Responsibility

Own the building-block runtime: component registration, name resolution, application scoping, and uniform invocation of building blocks regardless of the backing implementation.

## Owns

- Building-block registration
- Component-name resolution
- Application scoping of components
- Uniform invocation surface
- Runtime-level observability of calls

## Explicitly does not own

- Backing store and broker implementations
- Deployment topology
- Application code
- Authorization policy content
- Scheduling

## Non-goals

- Implementing stores or brokers
- Deploying itself
- Authoring authorization policy

## Interfaces

- `invoke` - PK_DAR_INVOKE/1 - a building-block call by component name
- `register` - PK_DAR_COMPONENT/1 - a named, typed, scoped component
- `scope` - PK_DAR_SCOPE/1 - which applications may reach a component

## Service-level objectives

- **scope containment** - zero calls reach a component outside the caller's scope (error budget: no budget)
- **portability** - swapping an implementation changes zero application calls (error budget: no budget)
- **overhead** - p99 runtime overhead under 1ms per call (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-46 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-46 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-46`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-46`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
