# INV-55 - Secrets integration

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Secrets integration lets an application reference a secret by name and get its value at run time without the value ever sitting in configuration, logs or the application's image. Access is scoped per application and per secret, values arrive with a version and a lease, and rotation is a new version rather than an overwrite.

## Responsibility

Own secret resolution for applications: reference-by-name, per-application scoping, versioned rotation, leased access and redaction of values from every log and error.

## Owns

- Secret references in configuration
- Per-application, per-secret access scoping
- Versioned rotation
- Leased (time-bounded) access
- Redaction of secret values

## Explicitly does not own

- Secret storage backends
- Key custody and HSMs
- Identity issuance
- Application logic
- Audit storage

## Non-goals

- Storing secrets
- Holding root keys
- Issuing identities

## Interfaces

- `resolve` - PK_SECRET_RESOLVE/1 - name to leased, versioned value
- `rotate` - PK_SECRET_ROTATE/1 - add a new version
- `scope` - PK_SECRET_SCOPE/1 - which apps may resolve which secrets

## Service-level objectives

- **no leakage** - zero secret values in logs or errors (error budget: no budget)
- **scoping** - zero resolutions outside scope (error budget: no budget)
- **resolution latency** - p99 under 5ms from cache (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-55 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-55 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-55`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-55`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
