# PLN-06 - Data plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The data plane separates control traffic from bulk movement and keeps data where gravity puts it. It admits a transfer only when the destination is a legal residence for the data's classification, and it picks a transport by payload size and locality rather than routing everything through the control path.

## Responsibility

Own bulk data movement: classify each transfer, refuse destinations that violate residency, select a transport tier by size and locality, and keep control traffic off the bulk path.

## Owns

- Transport tier selection for bulk payloads
- Data-residency admission for transfers
- Separation of control and bulk paths
- Backpressure on the bulk path
- Transfer integrity digests

## Explicitly does not own

- Storage backends
- Data classification policy authorship
- Control-plane messaging
- Encryption key custody
- Where a workload runs

## Non-goals

- Implementing storage
- Authoring residency policy
- Carrying control-plane messages
- Guaranteeing delivery across a partitioned WAN

## Interfaces

- `residency` - PK_RESIDENCY/1 - site residency labels and permitted classifications
- `tiers` - PK_TRANSPORT_TIER/1 - available transport tiers and their size bands
- `transfer` - PK_TRANSFER/1 - request a bulk transfer with classification and destination

## Service-level objectives

- **residency correctness** - zero transfers admitted to an illegal residence (error budget: no budget)
- **control isolation** - zero bulk payloads observed on the control transport (error budget: no budget)
- **bulk throughput** - p50 local-tier throughput at or above the node's measured line rate minus 10% (error budget: 5% of transfers may fall below)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-06`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-06`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
