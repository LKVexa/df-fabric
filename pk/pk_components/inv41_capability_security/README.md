# INV-41 - Capability security

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Capability security at the software level is the discipline the whole estate leans on: there is no ambient authority, a component can only do what it was handed, and handing something on can only narrow it. This element is where that rule is enforced for in-process references rather than for network grants.

## Responsibility

Own ambient-authority elimination inside a process: every resource is reached through an unforgeable reference that was explicitly passed in, delegation may only attenuate, and there is no global namespace from which authority can be recovered.

## Owns

- Unforgeable resource references
- Explicit delegation and attenuation
- Absence of a global or ambient namespace
- Revocation through membranes
- Refusal of authority recovery by name

## Explicitly does not own

- Hardware capability enforcement
- Network capability grants
- Policy authorship
- The language runtime
- Placement

## Non-goals

- Hardware enforcement
- Network grant issuance
- Global service discovery
- Recovering authority a component was not given

## Interfaces

- `attenuate` - PK_REFERENCE/1 - a narrower reference derived from a held one
- `grant` - PK_REFERENCE/1 - an unforgeable reference to one resource
- `membrane` - PK_MEMBRANE/1 - a revocable wrapper around a set of references

## Service-level objectives

- **no ambient authority** - zero resources reachable without a passed reference (error budget: no budget)
- **attenuation** - zero delegations widening authority (error budget: no budget)
- **revocation** - 100% of references behind a revoked membrane become unusable at once (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-41 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-41 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-41`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-41`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
