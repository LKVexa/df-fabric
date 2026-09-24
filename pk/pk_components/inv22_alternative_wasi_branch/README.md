# INV-22 - Alternative WASI branch

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The alternative WASI branch exists because the standards track is not the only consumer of these interfaces, and a fork that ships earlier will accumulate divergence. This element's job is to know exactly where the branches differ, translate what can be translated, and refuse -- loudly -- what cannot, rather than letting a component silently behave differently on each.

## Responsibility

Own branch divergence management: an explicit compatibility matrix per interface, bidirectional translation where semantics permit, refusal where they do not, and a conformance report that states which branch a component was certified against.

## Owns

- The per-interface compatibility matrix
- Bidirectional shims where semantics match
- Explicit refusal for semantically divergent interfaces
- Branch certification of a component
- Divergence drift reporting

## Explicitly does not own

- Either branch's specification
- Guest toolchains
- Runtime implementation
- Standards process
- Placement

## Non-goals

- Influencing either standards process
- Implementing a runtime
- Papering over semantic divergence with a lossy shim
- Guessing at an unclassified interface

## Interfaces

- `certify` - PK_BRANCH_CERT/1 - the branch a component is certified against
- `matrix` - PK_BRANCH_MATRIX/1 - per-interface compatibility classification
- `translate` - PK_BRANCH_SHIM/1 - a bidirectional shim for a compatible interface

## Service-level objectives

- **no silent divergence** - zero components run on an uncertified branch (error budget: no budget)
- **matrix completeness** - every interface in use is classified (error budget: no budget)
- **drift visibility** - divergence count reported every release (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-22 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-22 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-22`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-22`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
