# INV-21 - Local service chaining

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Local service chaining is what makes the component model pay off operationally: when component A calls component B and both are on the same host, the call never becomes a network request. It becomes a direct invocation, with the same interface, the same capability checks and the same observability -- the topology changes, the semantics do not.

## Responsibility

Own the local call path between co-resident components: resolution, the decision to chain locally or fall back to the network, loop prevention, depth bounding and preservation of identity and trace context across the hop.

## Owns

- Co-residency detection and local dispatch
- Chain depth and cycle bounding
- Identity and trace propagation across a local hop
- Fallback to the network path when the callee is remote
- Per-hop capability re-checking

## Explicitly does not own

- Placement decisions
- The network transport
- Interface definitions
- Service discovery beyond the local host
- Business logic

## Non-goals

- Deciding placement
- Implementing the network transport
- Changing call semantics for local hops
- Allowing cross-tenant local calls

## Interfaces

- `chain` - PK_LOCAL_CHAIN/1 - a call routed locally or remotely
- `depth` - PK_CHAIN_DEPTH/1 - the current chain depth and its bound
- `residency` - PK_RESIDENCY/1 - which components share this host

## Service-level objectives

- **semantic identity** - local and remote calls produce identical results (error budget: no budget)
- **tenant containment** - zero local calls across a tenant boundary (error budget: no budget)
- **local hop cost** - p99 local dispatch under 20us versus milliseconds over the network (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-21 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-21 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-21`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-21`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
