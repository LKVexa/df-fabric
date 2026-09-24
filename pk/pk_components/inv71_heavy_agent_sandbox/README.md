# INV-71 - Heavy agent sandbox

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The heavy agent sandbox is for code the fast sandbox cannot or should not hold: real interpreters, package installs, browsers. Each agent session gets its own microVM-class boundary with a filesystem that starts from a clean snapshot, egress limited to an allowlist, and a teardown that leaves nothing behind for the next session to find.

## Responsibility

Own the heavyweight session sandbox: per-session isolation, clean-snapshot filesystems, egress allowlists, resource limits and verified teardown.

## Owns

- Per-session isolation boundary
- Clean-snapshot filesystem per session
- Egress allowlisting
- Session resource limits
- Verified teardown

## Explicitly does not own

- Hypervisor implementation
- Tool business logic
- Model execution
- Credential issuance
- Long-term storage

## Non-goals

- Implementing hypervisors
- Running models
- Issuing credentials

## Interfaces

- `egress` - PK_HEAVYBOX_EGRESS/1 - an allow or deny decision
- `session` - PK_HEAVYBOX_SESSION/1 - an isolated agent session
- `teardown` - PK_HEAVYBOX_TEARDOWN/1 - a verified teardown record

## Service-level objectives

- **session isolation** - zero bytes carried from one session to another (error budget: no budget)
- **egress containment** - zero connections outside the allowlist (error budget: no budget)
- **session start** - p99 under 250ms from snapshot (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-71 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-71 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-71`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-71`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
