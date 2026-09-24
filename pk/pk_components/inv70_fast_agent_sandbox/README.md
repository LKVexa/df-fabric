# INV-70 - Fast agent sandbox

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The fast agent sandbox runs small pieces of untrusted logic in microseconds: a tiny stack machine with a fuel counter, a hard memory ceiling, and no host access except through capabilities the agent was granted. It is fast because it is small, and safe because a program that runs out of fuel, memory or permissions simply stops with a reason.

## Responsibility

Own the lightweight sandbox: a bounded interpreter, fuel metering, memory ceilings, capability-gated host calls and deterministic termination.

## Owns

- The bounded stack interpreter
- Fuel metering
- Memory ceiling
- Capability-gated host calls
- Deterministic termination with a reason

## Explicitly does not own

- High-risk arbitrary code
- Model execution
- Tool business logic
- Network access by default
- Persistent storage

## Non-goals

- Running arbitrary native code
- Granting network by default
- Persisting state

## Interfaces

- `hostcall` - PK_FASTBOX_HOSTCALL/1 - a capability-gated call
- `result` - PK_FASTBOX_RESULT/1 - value or termination reason
- `run` - PK_FASTBOX_RUN/1 - program, fuel, memory, capabilities

## Service-level objectives

- **termination** - every run terminates within its fuel (error budget: no budget)
- **containment** - zero host calls without capability (error budget: no budget)
- **startup** - p99 run start under 50us (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-70 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-70 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-70`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-70`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
