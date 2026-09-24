# INV-64 - Application model

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The application model is the declarative description of an application: its components, the providers they link to, and the traits -- scaling, spread -- attached to each. Its value is validation before anything runs: a link to a component that does not exist, a trait on a component that is not there, or a schema version the platform does not speak is refused at submit.

## Responsibility

Own the application manifest: schema versioning, component and provider declarations, link and trait validation, and a canonical form for diffing and signing.

## Owns

- Manifest schema and versions
- Component and provider declarations
- Link validation
- Trait validation
- Canonical manifest form

## Explicitly does not own

- Running applications
- Reconciliation
- Provider implementations
- Artifact storage
- Policy decisions

## Non-goals

- Running anything
- Reconciling
- Implementing providers

## Interfaces

- `canonical` - PK_APP_CANONICAL/1 - the canonical digest
- `manifest` - PK_APP_MANIFEST/1 - components, providers, links, traits
- `validate` - PK_APP_VALIDATE/1 - all validation errors

## Service-level objectives

- **fail at submit** - zero dangling links reach deployment (error budget: no budget)
- **canonical identity** - equivalent manifests share one digest (error budget: no budget)
- **validation time** - p99 under 5ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-64 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-64 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-64`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-64`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
