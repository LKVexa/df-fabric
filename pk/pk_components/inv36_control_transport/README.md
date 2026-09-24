# INV-36 - Control transport

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The control transport carries the small, authoritative messages -- placement decisions, leases, revocations -- that everything else acts on. Its job is not speed but trust: every frame is authenticated, sequenced and sealed end to end, so a relay in the middle forwards ciphertext it cannot read or reorder undetected.

## Responsibility

Own the control-message channel: session keying, per-frame authentication and sealing, sequence ordering, replay rejection and frame bounding, end to end across any relay.

## Owns

- Session establishment and key derivation
- Per-frame sealing and authentication
- Monotonic sequencing and replay rejection
- Frame size bounds
- End-to-end confidentiality across relays

## Explicitly does not own

- Bulk payload movement
- NAT traversal and relay selection
- Key custody
- Message semantics
- Scheduling

## Non-goals

- Moving bulk data
- Choosing relays
- Holding long-term keys
- Interpreting control messages

## Interfaces

- `frame` - PK_CTRL_FRAME/1 - one sealed, authenticated control frame
- `relay` - PK_CTRL_RELAY/1 - opaque forwarding of sealed frames
- `session` - PK_CTRL_SESSION/1 - a keyed, sequenced control session

## Service-level objectives

- **authenticity** - zero unauthenticated frames acted upon (error budget: no budget)
- **relay blindness** - zero plaintext bytes visible to any relay (error budget: no budget)
- **control latency** - p99 seal+open under 50us per frame (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-36 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-36 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-36`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-36`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
