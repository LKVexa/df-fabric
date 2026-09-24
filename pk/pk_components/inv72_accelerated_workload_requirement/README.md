# INV-72 - Accelerated workload requirement

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

An accelerated workload requirement is how a job says what hardware it actually needs: which accelerator class, how much device memory, how many devices, and whether they must share a fast interconnect. Matching is strict on what matters -- a job needing 80 GB is never placed on a 40 GB part -- and device sharing is allowed only when the tenant's isolation class permits partitioning.

## Responsibility

Own accelerator requirements: the requirement schema, strict matching against devices, interconnect constraints, and partition-sharing rules by isolation class.

## Owns

- The accelerator requirement schema
- Strict device matching
- Interconnect constraints
- Partitioned sharing rules
- Explained non-matches

## Explicitly does not own

- Device discovery
- Scheduling queues
- Driver management
- Model code
- Power policy

## Non-goals

- Discovering devices
- Queueing jobs
- Managing drivers

## Interfaces

- `match` - PK_ACCEL_MATCH/1 - selected devices or explained refusal
- `partition` - PK_ACCEL_PARTITION/1 - a shareable device slice
- `requirement` - PK_ACCEL_REQ/1 - class, memory, count, interconnect, isolation

## Service-level objectives

- **strict fit** - zero jobs placed below their memory requirement (error budget: no budget)
- **isolation** - zero partition shares across disallowed isolation classes (error budget: no budget)
- **match time** - p99 under 10ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-72 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-72 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-72`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-72`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
