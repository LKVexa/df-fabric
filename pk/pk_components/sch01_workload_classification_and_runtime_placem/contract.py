"""Binding contract for SCH-01 - Workload Classification and Runtime Placement Engine.

The multi-runtime scheduler is the piece Kubernetes does not have: it classifies a workload by trust, latency, and hardware need, then places it on a node that can actually honour that class. Classification and placement are separate steps, and a placement that would downgrade isolation is refused rather than made to fit.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "SCH-01"
ELEMENT_NAME = "Workload Classification and Runtime Placement Engine"


def build() -> Contract:
    """Return the production contract for SCH-01."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own workload classification and runtime placement: derive a trust class, latency class, and hardware requirement for every workload, and bind it to a node whose attested tiers and capacity satisfy that class, or refuse placement with the unmet constraint named."
        ),
        owns=[
            "Workload classification (trust, latency, hardware)",
            "Candidate node filtering against hard constraints",
            "Scoring and deterministic tie-breaking",
            "Placement binding and its lease",
            "Refusal when no node satisfies the hard constraints"
        ],
        not_owns=[
            "Isolation enforcement on the node",
            "Capacity targets",
            "Node provisioning",
            "Application composition",
            "Data residency policy"
        ],
        dependencies=[
            Dependency("PLN-02 Application plane", "upstream", "Supplies the resolved revision and its components"),
            Dependency("PLN-05 Elasticity plane", "upstream", "Supplies how many instances to place"),
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies each node's real capabilities"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits the placed workload to a tier"),
            Dependency("GAP-03 Topology-aware scheduler", "peer", "Supplies topology and locality costs"),
            Dependency("GAP-10 Power/thermal-aware scheduling", "peer", "May exclude a node under thermal pressure", required=False)
        ],
        source_of_truth="The node capability reports from hardware discovery; a capability that is not reported does not exist.",
        assumptions=[
            "Node capability reports may be stale or missing for disconnected sites",
            "A workload's trust class is derived from provenance, not self-declared",
            "Hard constraints are never traded away for a better score"
        ],
        boundaries={
            "tenant": "placement never co-locates two tenants at the same trust class on one tier instance",
            "environment": "scheduling is per environment; nodes do not serve two environments",
            "site": "site affinity and anti-affinity are hard constraints when declared",
            "workload": "each workload instance gets exactly one placement lease"
        },
        mandatory=[
            "Classify every workload for trust, latency, and hardware before placement",
            "Filter candidates on hard constraints before scoring",
            "Refuse placement when no candidate satisfies the hard constraints",
            "Break score ties deterministically",
            "Issue a placement lease that names the node and the required tier"
        ],
        optional=[
            "Topology-cost scoring",
            "Power-aware node exclusion",
            "Preemption of lower-class workloads",
            "Bin-packing beyond first-fit-decreasing"
        ],
        non_goals=[
            "Enforcing isolation",
            "Provisioning nodes",
            "Deciding instance counts",
            "Placing a workload on a node that cannot attest its required tier"
        ],
        interfaces={
            "classify": "PK_WORKLOAD_CLASS/1 - trust, latency, and hardware classification",
            "place": "PK_PLACEMENT/1 - placement request and its lease or refusal",
            "nodes": "PK_NODE_REPORT/1 - reported node capabilities, tiers, and free capacity"
        },
        threats=[
            "A workload self-declaring a lower trust class to reach a weaker tier",
            "A node over-reporting capabilities to attract workloads",
            "Placement starvation of a tenant by a noisy neighbour",
            "Scheduling oracle leakage revealing another tenant's placement",
            "Stale capability reports used to place onto a degraded node"
        ],
        failure_modes=[
            "No candidate node satisfies the hard constraints",
            "Node capability report is stale beyond the freshness bound",
            "Lease expires before the execution plane admits the workload",
            "Candidate set is empty because every node is thermally excluded"
        ],
        slos=[
            Slo("placement soundness", "zero placements onto a node lacking the required tier", "no budget"),
            Slo("placement latency", "p99 decision under 100ms for 1,000 candidate nodes", "1% may exceed"),
            Slo("determinism", "identical inputs produce an identical placement", "no budget")
        ],
        signals={
            "placements": "counter by trust class, tier, and outcome",
            "placement_refusals": "counter labelled by the unmet hard constraint",
            "candidate_set_size": "histogram of candidates surviving the filter",
            "placement_seconds": "histogram of decision latency",
            "stale_node_reports": "gauge of nodes excluded for report staleness"
        },
    )
