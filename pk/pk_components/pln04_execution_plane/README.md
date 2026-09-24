# PLN-04 - Execution plane

**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The execution plane admits a workload to a concrete isolation tier - Wasm component, microVM, unikernel, or full VM - and enforces that the tier actually delivers the isolation the workload's trust class requires. Placement chooses the node; this plane chooses and enforces the boundary.

## Responsibility

Own the isolation tiers available on a node, admit each workload to the weakest tier that still satisfies its trust class, and refuse admission when no available tier meets it.

## Owns

- The catalogue of isolation tiers on a node
- Trust-class to tier admission rules
- Tier capability attestation before admission
- Workload lifecycle within a tier
- Refusal of workloads no tier can isolate

## Explicitly does not own

- Which node a workload lands on
- Runtime internals of any tier
- Application composition
- Network policy
- Hardware capability discovery

## Non-goals

- Placement or scheduling
- Implementing the tiers themselves
- Admitting an untrusted workload to a process sandbox
- Cross-tenant tier reuse

## Interfaces

- `admit` - PK_ADMISSION/1 - request admission for a workload at a trust class
- `catalogue` - PK_TIER_CATALOGUE/1 - attested tiers available on this node
- `lifecycle` - PK_TIER_LIFECYCLE/1 - start, stop, and teardown events

## Service-level objectives

- **admission latency** - p99 admission decision under 50ms (error budget: 1% may exceed)
- **isolation correctness** - zero workloads admitted below their required tier (error budget: no budget)
- **teardown** - 99.99% of tier instances fully torn down before reuse of their resources (error budget: 0.01% escalate to node drain)

## Running it

```
python -m pk_core list
python -m pk_core run PLN-04 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-04 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-04`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-04`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
