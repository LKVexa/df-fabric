# INV-44 - Wasm hardening system

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The Wasm hardening system is what turns a Wasm runtime from a portability layer into an isolation boundary: guard pages, control-flow integrity, bounded fuel, and a compiler whose output is verified rather than trusted. A hardened runtime with one of these off is not a hardened runtime, and this element says so.

## Responsibility

Own the hardened Wasm runtime configuration: require the full hardening set, verify compiled module output before execution, enforce fuel and memory ceilings at run time, and refuse to execute under a partial hardening configuration.

## Owns

- The required hardening feature set
- Post-compilation output verification
- Fuel metering and its exhaustion behaviour
- Linear-memory ceiling enforcement
- Refusal of partially hardened configurations

## Explicitly does not own

- The Wasm specification
- Compiler implementation
- Module source
- The host image
- Placement

## Non-goals

- Implementing the compiler
- Extending the Wasm specification
- Running unhardened for performance
- Trusting compiler output unverified

## Interfaces

- `configure` - PK_WASM_HARDENING/1 - the hardening feature set and its applied state
- `instantiate` - PK_WASM_INSTANCE/1 - a verified, metered module instance

## Service-level objectives

- **hardening completeness** - zero instances executed with a partial hardening set (error budget: no budget)
- **output verification** - 100% of compiled modules verified before execution (error budget: no budget)
- **memory ceiling** - zero instances growing past their declared ceiling (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-44 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-44 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-44`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-44`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
