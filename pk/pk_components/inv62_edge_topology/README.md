# INV-62 - Edge topology

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Edge topology is the shape of the estate: cloud regions, sites, and devices at the far end, connected by links of very different latency and reliability. This element keeps that graph, answers 'what is nearest that can serve this?', and keeps a site working when its uplink goes -- a partitioned site elects a local coordinator instead of stopping.

## Responsibility

Own the topology graph: tiers, links and their latencies, nearest-capable resolution, and partition handling with site-local coordination.

## Owns

- The tier hierarchy (cloud, region, site, device)
- Link latency and health
- Nearest-capable node resolution
- Partition detection
- Site-local coordinator election

## Explicitly does not own

- Workload scheduling
- WAN transport
- Device provisioning
- Data placement
- Hardware discovery

## Non-goals

- Scheduling
- Transport
- Provisioning

## Interfaces

- `graph` - PK_TOPO_GRAPH/1 - nodes, tiers, links
- `nearest` - PK_TOPO_NEAREST/1 - nearest capable node
- `partition` - PK_TOPO_PARTITION/1 - partition state and local coordinator

## Service-level objectives

- **reachability** - zero routes across down links (error budget: no budget)
- **partition continuity** - a partitioned site elects a coordinator within 5s (error budget: 1% may exceed)
- **resolution time** - p99 nearest query under 1ms (error budget: 1% may exceed)

## Running it

```
python -m pk_core list
python -m pk_core run INV-62 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-62 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-62`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-62`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
