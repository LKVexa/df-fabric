# INV-37 - Bulk data plane

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The bulk data plane moves the large things -- images, snapshots, model weights, datasets -- in verified chunks. Every chunk carries its own digest and the object carries a digest over the chunk list, so a transfer is checked end to end by the receiver, can resume from the last good chunk, and never trusts the transport to have delivered what it claims.

## Responsibility

Own chunked bulk transfer: chunking, per-chunk and whole-object digests, receiver-side end-to-end verification, resumption and bounded concurrency.

## Owns

- Content chunking and manifests
- Per-chunk digest verification
- Whole-object end-to-end verification
- Resumable transfer state
- Transfer concurrency bounds

## Explicitly does not own

- Control messages
- Placement of data
- Storage backends
- Encryption key custody
- Deciding what to move

## Non-goals

- Carrying control messages
- Choosing placement
- Implementing storage

## Interfaces

- `chunk` - PK_BULK_CHUNK/1 - one digested chunk
- `manifest` - PK_BULK_MANIFEST/1 - chunk list and object digest
- `resume` - PK_BULK_RESUME/1 - the last verified chunk index

## Service-level objectives

- **integrity** - zero objects accepted without end-to-end digest verification (error budget: no budget)
- **resumption** - an interrupted transfer re-sends only unverified chunks (error budget: no budget)
- **throughput** - p50 throughput within 10% of link capacity (error budget: 5% of transfers may fall below)

## Running it

```
python -m pk_core list
python -m pk_core run INV-37 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-37 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-37`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-37`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
