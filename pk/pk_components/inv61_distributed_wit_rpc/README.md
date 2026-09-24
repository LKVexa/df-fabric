# INV-61 - Distributed WIT RPC

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Distributed WIT RPC carries typed interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments.

## Responsibility

Own cross-host typed invocation: frame format, signature fingerprints, receiver-side compatibility checks, typed error returns and deadlines.

## Owns

- RPC frame format
- Signature fingerprinting
- Receiver-side compatibility check
- Typed error returns
- Per-call deadlines

## Explicitly does not own

- Interface definitions
- Transport encryption
- Service discovery
- Component logic
- Load balancing

## Non-goals

- Defining interfaces
- Encrypting transport
- Discovering services

## Interfaces

- `deadline` - PK_WRPC_DEADLINE/1 - absolute call deadline
- `error` - PK_WRPC_ERROR/1 - a typed error result
- `frame` - PK_WRPC_FRAME/1 - interface, version, function, fingerprint, args

## Service-level objectives

- **no misreads** - zero frames decoded against a mismatched signature (error budget: no budget)
- **deadlines** - zero calls outliving their deadline (error budget: no budget)
- **overhead** - p99 framing overhead under 50us (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-61 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-61 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-61`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-61`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
