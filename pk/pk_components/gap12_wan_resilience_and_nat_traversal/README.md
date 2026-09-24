# GAP-12 - WAN resilience and NAT traversal

**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

WAN resilience and NAT traversal is the plumbing that keeps an edge site reachable from behind a carrier-grade NAT on a flaky link. It escalates through connection strategies in cost order, backs off honestly, and reports the link as down rather than pretending a stale path still works.

## Responsibility

Own reachability to and from edge sites across hostile networks: escalate through direct, hole-punched and relayed paths in cost order, apply bounded exponential backoff, and report a partition rather than masking it.

## Owns

- Connection strategy escalation and its order
- NAT traversal attempts and their outcomes
- Backoff schedule and its bounds
- Path health and the partition verdict
- Relay fallback and its cost accounting

## Explicitly does not own

- Transport encryption
- Data replication semantics
- Autonomy policy during partition
- Application protocols
- Relay infrastructure provisioning

## Non-goals

- Encrypting traffic
- Provisioning relays
- Deciding what to do during a partition
- Guaranteeing connectivity through a severed link

## Interfaces

- `backoff` - PK_BACKOFF/1 - the current retry schedule and its bound
- `connect` - PK_PATH_REQUEST/1 - establish a path to a peer site
- `path` - PK_PATH_STATE/1 - current strategy, health and last successful probe

## Service-level objectives

- **path honesty** - zero paths reported healthy without a probe inside the freshness window (error budget: no budget)
- **escalation order** - zero relay fallbacks before cheaper strategies were tried (error budget: no budget)
- **backoff bound** - retry interval never exceeds the declared ceiling (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run GAP-12 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-12 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-12`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-12`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
