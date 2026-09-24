"""Binding contract for INV-68 - Resource packing.

Resource packing decides how many workloads fit on how many hosts. Packing well means fewer hosts for the same work; packing carelessly means one dimension -- usually memory -- runs out while CPU sits idle. The packer places across every dimension at once, keeps a headroom reserve, and reports the fragmentation it leaves behind.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-68"
ELEMENT_NAME = "Resource packing"


def build() -> Contract:
    """Return the production contract for INV-68."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own multi-dimensional bin packing: first-fit-decreasing placement, headroom reservation, overcommit ratios by dimension and fragmentation reporting."
        ),
        owns=[
            "Multi-dimensional placement",
            "Headroom reservation",
            "Per-dimension overcommit ratios",
            "Fragmentation reporting",
            "Packing efficiency against a naive baseline"
        ],
        not_owns=[
            "Workload classification",
            "Host provisioning",
            "Thermal policy",
            "Accelerator matching",
            "Preemption"
        ],
        dependencies=[
            Dependency("INV-67 Kubernetes integration mechanism", "upstream", "Supplies translated resource requests"),
            Dependency("SCH-01 Multi-runtime scheduler", "upstream", "Asks where a batch of work fits"),
            Dependency("GAP-10 Power/thermal-aware scheduling", "downstream", "Adds power limits on top of the packing"),
            Dependency("INV-72 Accelerated workload requirement", "peer", "Handles accelerator dimensions separately")
        ],
        source_of_truth="The host capacity ledger; a placement is valid only if every dimension still fits after headroom.",
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
            "Check every dimension before placing",
            "Keep a headroom reserve on every host",
            "Never overcommit memory",
            "Place largest-first",
            "Report fragmentation after packing"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Classifying workloads",
            "Provisioning hosts",
            "Matching accelerators"
        ],
        interfaces={
            "pack": "PK_PACK/1 - workloads to host assignments",
            "capacity": "PK_PACK_CAPACITY/1 - per-host, per-dimension capacity",
            "fragmentation": "PK_PACK_FRAG/1 - stranded capacity report"
        },
        threats=[
            "Memory overcommit leading to OOM kills",
            "Headroom consumed leaving no room for failover",
            "Stranded capacity hiding the need for more hosts"
        ],
        failure_modes=[
            "Workload fits nowhere",
            "Dimension exhausted",
            "Headroom breached",
            "Capacity data stale"
        ],
        slos=[
            Slo("no memory overcommit", "zero hosts with memory placed above capacity minus headroom", "no budget"),
            Slo("efficiency", "hosts used within 10% of the lower bound", "5% of batches may exceed"),
            Slo("pack time", "p99 under 100ms for 1000 workloads", "1% may exceed")
        ],
        signals={
            "hosts_used": "gauge",
            "unplaced": "counter",
            "stranded_cpu": "gauge",
            "stranded_mem": "gauge"
        },
    )
