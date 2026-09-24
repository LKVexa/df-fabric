# GAP-07 - Artifact provenance/signing

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Artifact provenance and signing is the estate's supply-chain gate. Nothing executable or policy-bearing is consumed without a signature chaining to a trusted root, and the signature covers the artifact's digest, so swapping the bytes under a valid signature fails.

## Responsibility

Own artifact signing and verification: bind every executable or policy artifact to its digest and a signer in the trust store, and refuse consumption of anything unsigned, mis-signed, revoked, or digest-mismatched.

## Owns

- The trust store of accepted signers
- Artifact signing and signature format
- Digest binding between signature and bytes
- Signer revocation
- Provenance chain from source to deployed artifact

## Explicitly does not own

- Key custody and generation
- What an artifact does once admitted
- Node attestation
- Policy authorship
- Artifact transport

## Non-goals

- Generating or storing private keys
- Judging artifact behaviour
- Attesting nodes
- Guaranteeing revocation reaches a partitioned site instantly

## Interfaces

- `provenance` - PK_PROVENANCE/1 - the chain from source to deployed artifact
- `sign` - PK_SIGNATURE/1 - produce a digest-bound signature for an artifact
- `trust` - PK_TRUST_STORE/1 - accepted signers, their roles, and revocations
- `verify` - PK_VERIFICATION/1 - verify a signature against the trust store

## Service-level objectives

- **verification soundness** - zero artifacts admitted whose digest does not match their signature (error budget: no budget)
- **revocation** - zero artifacts admitted from a signer revoked in the local trust store (error budget: no budget)
- **verification latency** - p99 verification under 2ms per artifact (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-07 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-07 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-07`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-07`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
