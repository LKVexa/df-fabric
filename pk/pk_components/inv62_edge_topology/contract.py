"""Binding contract for INV-62 - Edge topology.

Edge topology is the shape of the estate: cloud regions, sites, and devices at the far end, connected by links of very different latency and reliability. This element keeps that graph, answers 'what is nearest that can serve this?', and keeps a site working when its uplink goes -- a partitioned site elects a local coordinator instead of stopping.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-62"
ELEMENT_NAME = "Edge topology"


def build() -> Contract:
    """Return the production contract for INV-62."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the topology graph: tiers, links and their latencies, nearest-capable resolution, and partition handling with site-local coordination."
        ),
        owns=[
            "The tier hierarchy (cloud, region, site, device)",
            "Link latency and health",
            "Nearest-capable node resolution",
            "Partition detection",
            "Site-local coordinator election"
        ],
        not_owns=[
            "Workload scheduling",
            "WAN transport",
            "Device provisioning",
            "Data placement",
            "Hardware discovery"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies what each node can serve"),
            Dependency("GAP-12 WAN resilience and NAT traversal", "upstream", "Reports link health"),
            Dependency("GAP-03 Topology-aware scheduler", "downstream", "Places work using this graph"),
            Dependency("GAP-04 Disconnected operation controller", "peer", "Runs the site while partitioned")
        ],
        source_of_truth="The topology graph with measured link latencies; a node's own idea of its location is advisory.",
        assumptions=[
            "Every peer, network path and store can fail independently",
            "Callers are untrusted until their identity is established",
            "Behaviour must be identical whether a dependency is local or remote"
        ],
        boundaries={
            "tenant": "state and traffic are partitioned per tenant and never shared",
            "environment": "limits and endpoints differ per environment",
            "site": "each site runs its own instance; nothing assumes a global singleton",
            "workload": "budgets and quotas are per workload"
        },
        mandatory=[
            "Model every node in a tier with its parent",
            "Resolve the lowest-latency capable node",
            "Detect when a site loses its uplink",
            "Elect a local coordinator in a partitioned site",
            "Never route across a down link"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Scheduling",
            "Transport",
            "Provisioning"
        ],
        interfaces={
            "graph": "PK_TOPO_GRAPH/1 - nodes, tiers, links",
            "nearest": "PK_TOPO_NEAREST/1 - nearest capable node",
            "partition": "PK_TOPO_PARTITION/1 - partition state and local coordinator"
        },
        threats=[
            "Routing through a dead uplink",
            "Split coordination after partition",
            "Stale latency sending work to a far node"
        ],
        failure_modes=[
            "No capable node reachable",
            "Uplink down",
            "Coordinator election tie",
            "Latency data stale"
        ],
        slos=[
            Slo("reachability", "zero routes across down links", "no budget"),
            Slo("partition continuity", "a partitioned site elects a coordinator within 5s", "1% may exceed"),
            Slo("resolution time", "p99 nearest query under 1ms", "1% may exceed")
        ],
        signals={
            "nodes": "gauge by tier",
            "links_down": "gauge",
            "partitions": "counter",
            "local_elections": "counter"
        },
    )
