# GAP-06 - Device identity and attestation

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Device identity and attestation is where trust actually starts. A node proves what it is with evidence rooted in hardware, that evidence expires, and a node whose measurements drifted from the accepted set is untrusted even if it was trusted a minute ago.

## Responsibility

Own node identity and the attestation lifecycle: bind each node to a hardware-rooted identity, verify its measurements against an accepted set, and expire the verdict so trust is continuously re-earned rather than granted once.

## Owns

- Node identity binding to a hardware root
- Attestation evidence verification
- The accepted measurement set and its versioning
- Attestation verdict expiry
- Quarantine of nodes whose measurements drifted

## Explicitly does not own

- Capability probing
- Artifact signing
- Policy authorship
- Node lifecycle
- Grant issuance

## Non-goals

- Granting capabilities
- Signing artifacts
- Probing hardware capability
- Trusting a node because it was trusted previously

## Interfaces

- `attest` - PK_ATTESTATION/1 - submit evidence and receive a verdict with expiry
- `enrol` - PK_NODE_IDENTITY/1 - bind a node to a hardware-rooted identity
- `measurements` - PK_ACCEPTED_MEASUREMENTS/1 - the environment's accepted measurement set

## Service-level objectives

- **verdict soundness** - zero attested verdicts for measurements outside the accepted set (error budget: no budget)
- **replay resistance** - zero verdicts issued for evidence reusing a spent nonce (error budget: no budget)
- **re-attestation** - 99.9% of nodes re-attest before their verdict expires (error budget: 0.1% fall to untrusted and are cordoned)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-06`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-06`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
