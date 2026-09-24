# INV-60 - Wasm application fabric

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

A Wasm application fabric runs components across a lattice of hosts and wires them to capability providers by link name at run time. A component says 'I need a key-value store'; the fabric links it to one, routes calls across hosts, and restarts it elsewhere if a host goes. Artifacts are content-addressed, so what runs is exactly what was signed.

## Responsibility

Own the lattice runtime: host membership, component instantiation from content-addressed artifacts, run-time linking to providers, cross-host call routing and failover.

## Owns

- Lattice host membership
- Content-addressed component instantiation
- Run-time links to providers
- Cross-host call routing
- Failover of components off lost hosts

## Explicitly does not own

- Declarative deployment specs
- Provider implementations
- Artifact signing
- The component model
- Edge topology decisions

## Non-goals

- Declaring deployments
- Implementing providers
- Signing artifacts

## Interfaces

- `call` - PK_LATTICE_CALL/1 - a routed cross-host invocation
- `instantiate` - PK_LATTICE_START/1 - a component from a digest reference
- `link` - PK_LATTICE_LINK/1 - component, link name, provider

## Service-level objectives

- **artifact integrity** - zero components started from mismatched bytes (error budget: no budget)
- **failover** - components on a lost host restarted within 10s (error budget: 1% may exceed)
- **routing overhead** - p99 cross-host call overhead under 3ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-60 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-60 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-60`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-60`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
