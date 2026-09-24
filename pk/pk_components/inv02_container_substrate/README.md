# INV-02 - Container substrate

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The container substrate is the packaging layer the estate runs on today: images made of layers, pulled by name, run by a runtime. The weakness is the name -- a tag can be moved to point at different bytes. This element resolves every image to a content digest, checks the manifest against its layers, and refuses mutable tags wherever reproducibility matters.

## Responsibility

Own image identity and integrity: digest resolution, manifest and layer verification, tag-mutability policy by environment and layer de-duplication.

## Owns

- Tag-to-digest resolution
- Manifest verification against layer digests
- Mutable-tag policy
- Layer de-duplication
- Image provenance records

## Explicitly does not own

- Image building
- Runtime execution
- Hardening policy
- Registry operation
- Signing keys

## Non-goals

- Building images
- Running containers
- Operating registries

## Interfaces

- `policy` - PK_IMAGE_TAGPOLICY/1 - where mutable tags are allowed
- `resolve` - PK_IMAGE_RESOLVE/1 - reference to digest
- `verify` - PK_IMAGE_VERIFY/1 - manifest and layer verification

## Service-level objectives

- **integrity** - zero images run whose layers fail verification (error budget: no budget)
- **reproducibility** - zero production workloads referenced by mutable tag (error budget: no budget)
- **pull efficiency** - shared layers stored once (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-02`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-02`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
