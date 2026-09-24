# PLN-07 - Security plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The security plane replaces ambient trust with explicit, attenuable capabilities. Nothing in the estate holds authority it was not granted; every grant names its holder, its scope, and its expiry, and any holder may attenuate a grant but never widen one.

## Responsibility

Own capability issuance, attenuation, and verification for the estate: every authority is an explicit, scoped, expiring grant, and no path exists to widen a grant after issue.

## Owns

- Capability grant issuance and format
- Attenuation semantics
- Grant verification and expiry
- Trust-class definitions
- Revocation and the revocation horizon

## Explicitly does not own

- Identity provisioning
- Hardware attestation roots
- Policy authorship
- Enforcement points in other planes
- Secret material storage

## Non-goals

- Provisioning identities
- Storing secrets
- Enforcing grants on behalf of other planes
- Instantaneous revocation

## Interfaces

- `attenuate` - PK_GRANT/1 - derive a strictly narrower grant from a held one
- `issue` - PK_GRANT/1 - issue a scoped, expiring capability grant
- `revoke` - PK_REVOCATION/1 - publish a revocation with its horizon
- `verify` - PK_GRANT_VERIFICATION/1 - verify a grant chain at a point in time

## Service-level objectives

- **widening** - zero grants verified whose scope exceeds their parent (error budget: no budget)
- **expiry** - zero expired grants accepted outside the declared skew allowance (error budget: no budget)
- **verification latency** - p99 chain verification under 1ms for depth 5 (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-07 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-07 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-07`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-07`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
