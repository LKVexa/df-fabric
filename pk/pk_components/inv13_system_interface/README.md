# INV-13 - System interface

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The system interface is WASI: the component's only door to the outside world. Nothing is ambient -- no implicit filesystem, no implicit clock, no implicit network. A component gets exactly the preopened handles its world declared, and asks for anything else in vain.

## Responsibility

Own the host-interface surface a component sees: grant only the capabilities its declared world lists, resolve every path against a preopened directory, and refuse any request for a resource the component was not given.

## Owns

- The world declaration a component is instantiated against
- Preopened handle tables
- Path resolution confined to preopens
- Refusal of undeclared capability requests
- Clock and randomness capability gating

## Explicitly does not own

- Host implementations behind the interface
- Interface type definitions
- The canonical ABI
- Composition linking
- Placement

## Non-goals

- Implementing filesystems or networks
- Providing a default environment
- Resolving absolute paths
- Granting a capability because it seems harmless

## Interfaces

- `preopen` - PK_PREOPEN/1 - a granted directory handle and its root
- `resolve` - PK_PATH_RESOLVE/1 - a path resolved within a preopen
- `world` - PK_WORLD/1 - the capabilities a component is instantiated with

## Service-level objectives

- **confinement** - zero paths resolved outside a preopen (error budget: no budget)
- **no ambient** - zero capabilities granted that the world did not declare (error budget: no budget)
- **resolve latency** - p99 under 1us per path (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-13 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-13 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-13`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-13`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
