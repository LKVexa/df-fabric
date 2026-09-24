# INV-67 - Kubernetes integration mechanism

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The Kubernetes integration mechanism lets existing manifests and tooling drive the new runtime during migration. It translates the supported subset of a pod spec into a runtime placement request -- and is loud about the rest: a privileged container or a hostPath mount is refused with the field named, never silently dropped into a workload that then behaves differently.

## Responsibility

Own the Kubernetes bridge: pod-spec translation, explicit refusal of unsupported fields, label and resource mapping, and status projected back into Kubernetes terms.

## Owns

- Pod-spec subset translation
- Explicit refusal of unsupported fields
- Label and annotation mapping
- Resource request mapping
- Status projection back to Kubernetes

## Explicitly does not own

- The Kubernetes API server
- Runtime placement decisions
- Image building
- Cluster networking
- Operators

## Non-goals

- Running an API server
- Deciding placement
- Building images

## Interfaces

- `refuse` - PK_K8S_REFUSE/1 - unsupported fields named
- `status` - PK_K8S_STATUS/1 - runtime state as pod phase
- `translate` - PK_K8S_TRANSLATE/1 - pod spec to placement request

## Service-level objectives

- **no silent drops** - every unsupported field refused by name (error budget: no budget)
- **fidelity** - requests and limits preserved exactly (error budget: no budget)
- **translation time** - p99 under 5ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-67 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-67 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-67`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-67`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
