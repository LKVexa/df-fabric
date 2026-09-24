# INV-35 - High-performance VM I/O

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

High-performance VM I/O is virtio done properly: shared-memory rings, notification suppression and a vhost-style datapath that keeps the VMM out of the hot path. Every one of those tricks is also a way for a guest to corrupt the host, so descriptor validation here is not optional.

## Responsibility

Own the guest-host I/O datapath: validate every descriptor a guest places on a ring against the guest's own memory bounds, bound in-flight work per queue, and refuse a descriptor that would read or write outside the guest's memory.

## Owns

- Virtqueue descriptor validation
- Guest memory bounds checking on the datapath
- In-flight depth per queue
- Notification suppression and its correctness
- Refusal of malformed or out-of-bounds descriptors

## Explicitly does not own

- Device semantics
- Guest drivers
- The network or storage backend
- Device model membership
- Placement

## Non-goals

- Implementing device semantics
- Writing guest drivers
- Trusting a descriptor because the ring index moved
- Backend storage or networking

## Interfaces

- `complete` - PK_VIRTQUEUE_COMPLETE/1 - completion and notification decision
- `submit` - PK_VIRTQUEUE_SUBMIT/1 - a guest-posted descriptor chain

## Service-level objectives

- **memory safety** - zero descriptors dereferenced outside guest memory (error budget: no budget)
- **liveness** - zero lost wakeups with work pending (error budget: no budget)
- **throughput** - p50 at or above 90% of the backend's line rate (error budget: 5% may fall below)

## Running it

```
python -m pk_core list
python -m pk_core run INV-35 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-35 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-35`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-35`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
