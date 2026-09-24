"""Binding contract for INV-08 - Dynamic infrastructure model.

The dynamic infrastructure model treats capacity as something borrowed, not owned: nodes join a pool on a lease, are reclaimed when the lease lapses, and the pool grows and shrinks between hard bounds as demand changes. Two things must never happen -- unbounded growth, and a node reclaimed while it is still running work.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-08"
ELEMENT_NAME = "Dynamic infrastructure model"


def build() -> Contract:
    """Return the production contract for INV-08."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own elastic capacity: lease-based node membership, demand-driven scaling within bounds, safe reclamation of idle nodes and cost accounting."
        ),
        owns=[
            "Leased node membership",
            "Demand-driven scale-out and scale-in",
            "Hard pool bounds",
            "Safe reclamation of idle nodes",
            "Cost accounting per pool"
        ],
        not_owns=[
            "Provider provisioning APIs",
            "Workload scheduling",
            "Image building",
            "Billing systems",
            "Networking"
        ],
        dependencies=[
            Dependency("INV-06 Traditional IaC", "upstream", "The static model this replaces for elastic pools"),
            Dependency("INV-68 Resource packing", "downstream", "Packs work onto the current pool"),
            Dependency("PLN-05 Elasticity plane", "upstream", "Sets the demand signal and bounds"),
            Dependency("INV-32 Elastic virtualization", "peer", "Elasticity within a single host")
        ],
        source_of_truth="The lease table; a node that is not leased is not part of the pool.",
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
            "Admit nodes only on a lease",
            "Scale toward demand within hard bounds",
            "Reclaim only idle nodes whose lease lapsed or are surplus",
            "Renew leases for busy nodes",
            "Account cost per node-hour"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Provisioning hardware",
            "Scheduling work",
            "Billing"
        ],
        interfaces={
            "lease": "PK_DYN_LEASE/1 - node lease and expiry",
            "scale": "PK_DYN_SCALE/1 - scaling decision",
            "cost": "PK_DYN_COST/1 - node-hours per pool"
        },
        threats=[
            "Runaway scale-out",
            "Busy node reclaimed mid-job",
            "Leaked nodes accruing cost"
        ],
        failure_modes=[
            "Bound reached",
            "Lease expired",
            "Provisioning failed",
            "Reclaim blocked by work"
        ],
        slos=[
            Slo("bounded", "pool never exceeds its maximum", "no budget"),
            Slo("safe reclaim", "zero busy nodes reclaimed", "no budget"),
            Slo("responsiveness", "scale decision within one tick of demand change", "1% may exceed")
        ],
        signals={
            "pool_size": "gauge",
            "leases_expired": "counter",
            "reclaims": "counter",
            "node_hours": "counter"
        },
    )
