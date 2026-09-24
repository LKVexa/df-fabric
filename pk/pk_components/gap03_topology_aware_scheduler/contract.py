"""Binding contract for GAP-03 - Topology-aware scheduler.

The topology-aware scheduler supplies what a flat scheduler cannot: locality cost and fair share. It scores candidates by how far they are from the data and the caller, and it refuses to let one tenant's demand crowd out another's floor.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-03"
ELEMENT_NAME = "Topology-aware scheduler"


def build() -> Contract:
    """Return the production contract for GAP-03."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own topology cost and fair-share scoring for placement: rank candidate nodes by locality distance and enforce each tenant's reserved share so no tenant is starved by a noisier neighbour."
        ),
        owns=[
            "The topology graph and its distance metric",
            "Locality cost scoring",
            "Per-tenant fair-share reservations",
            "Starvation detection and the fairness guard",
            "Anti-affinity spreading across failure domains"
        ],
        not_owns=[
            "Hard constraint filtering",
            "Trust classification",
            "Capacity targets",
            "Node lifecycle",
            "Data residency policy"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies node facts the topology graph annotates"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Consumes the locality cost and fairness verdict"),
            Dependency("GAP-14 Data-gravity manager", "peer", "Supplies where the data already sits"),
            Dependency("PLN-05 Elasticity plane", "peer", "Supplies how much capacity each tenant is asking for", required=False)
        ],
        source_of_truth="The declared topology graph; measured latency refines a cost but never invents an edge.",
        assumptions=[
            "Topology is a tree of regions, sites and racks, not a flat set",
            "Measured latency is noisy and may be missing for a cold path",
            "A tenant's reserved share may exceed what is currently free"
        ],
        boundaries={
            "tenant": "each tenant carries a reserved share that scoring may not spend",
            "environment": "topology graphs are per environment",
            "site": "a site is a failure domain for anti-affinity purposes",
            "workload": "spreading is evaluated per workload group, not per instance"
        },
        mandatory=[
            "Compute a deterministic locality cost between any two topology nodes",
            "Refuse to score a candidate outside the declared topology",
            "Enforce each tenant's reserved share before serving surplus demand",
            "Spread a workload group across failure domains when asked",
            "Report the fairness verdict alongside the score"
        ],
        optional=[
            "Latency-measured cost refinement",
            "Cost caching",
            "Multi-objective scoring weights"
        ],
        non_goals=[
            "Hard constraint filtering",
            "Owning the placement decision",
            "Provisioning capacity to satisfy a share",
            "Guaranteeing a share that was never reserved"
        ],
        interfaces={
            "topology": "PK_TOPOLOGY/1 - the region/site/rack graph and its edges",
            "cost": "PK_LOCALITY_COST/1 - distance between two topology nodes",
            "fairness": "PK_FAIR_SHARE/1 - reserved shares and the starvation verdict"
        },
        threats=[
            "A tenant declaring a share it is not entitled to",
            "Topology forgery pulling work toward an attacker's rack",
            "Fairness bypass through workload-group splitting",
            "Latency injection to make a rival's site look far"
        ],
        failure_modes=[
            "Candidate node absent from the topology graph",
            "Reserved shares oversubscribe the estate",
            "Anti-affinity cannot be satisfied within the candidate set",
            "Latency measurement missing for a required edge"
        ],
        slos=[
            Slo("share enforcement", "zero placements spending another tenant's reserved share", "no budget"),
            Slo("cost determinism", "identical topology and candidates produce identical costs", "no budget"),
            Slo("scoring latency", "p99 scoring under 20ms for 1,000 candidates", "1% may exceed")
        ],
        signals={
            "locality_cost": "histogram of chosen-candidate cost by tenant",
            "fairness_denials": "counter of candidates refused for spending a reserved share",
            "starved_tenants": "gauge of tenants below their reserved share",
            "spread_failures": "counter of anti-affinity requests that could not be satisfied"
        },
    )
