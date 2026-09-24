# PLN-02 - Application plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The application plane is where an application is described as a composition of components and the capabilities they require, rather than as a bag of containers and YAML. It resolves a composition against available capability providers and refuses to admit an application whose required capabilities cannot be satisfied.

## Responsibility

Own the application model: resolve a declared composition of components and required capabilities into a satisfiable, versioned application revision, or reject it with the unsatisfied requirement named.

## Owns

- The application model and component composition graph
- Capability requirement resolution against providers
- Application revision identity and immutability
- Interface compatibility checks between composed components
- Rejection of unsatisfiable compositions

## Explicitly does not own

- Where a component runs
- The runtime that executes a component
- Capability provider implementations
- Network transport between components
- Desired state of the estate

## Non-goals

- Scheduling or placement
- Running components
- Implementing capability providers
- Mutating an already-published revision

## Interfaces

- `catalogue` - PK_PROVIDER_CATALOGUE/1 - available capability providers for an environment
- `compose` - PK_APPLICATION/1 - declare components, edges, and capability requirements
- `resolve` - PK_APPLICATION_REVISION/1 - immutable resolved revision with provider bindings

## Service-level objectives

- **resolution latency** - p99 resolution under 500ms for compositions up to 200 components (error budget: 1% may exceed)
- **revision immutability** - zero published revisions mutated after resolution (error budget: no budget)
- **resolution soundness** - zero revisions published with an unsatisfied required capability (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-02`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-02`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
