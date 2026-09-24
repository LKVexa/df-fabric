"""Binding contract for GAP-14 - Data-gravity manager.

The data-gravity manager decides whether the computation moves to the data or the data moves to the computation. It costs both directions honestly against residency and egress, and it will recommend neither rather than propose a move that residency forbids.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-14"
ELEMENT_NAME = "Data-gravity manager"


def build() -> Contract:
    """Return the production contract for GAP-14."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the move-compute-or-move-data decision: cost both directions against size, locality and egress, eliminate options residency forbids, and recommend the cheaper legal option or none at all."
        ),
        owns=[
            "Dataset location and size accounting",
            "Cost model for moving data versus moving compute",
            "Residency-legal option filtering",
            "The gravity recommendation and its reasoning",
            "Refusal when no legal option exists"
        ],
        not_owns=[
            "Executing the move",
            "Residency policy authorship",
            "Transport",
            "Placement decisions",
            "Storage engines"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Supplies residency rules the options are filtered against"),
            Dependency("GAP-03 Topology-aware scheduler", "upstream", "Supplies locality distance between sites"),
            Dependency("PLN-06 Data plane", "downstream", "Executes an approved data move"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Places compute where this element recommends"),
            Dependency("GAP-05 State replication/consistency model", "peer", "Reports whether a dataset has converged before it moves")
        ],
        source_of_truth="The residency verdict from the policy engine; a cheaper option that residency forbids does not exist.",
        assumptions=[
            "Egress is charged asymmetrically and dominates at scale",
            "Moving compute is usually cheaper than moving a large dataset",
            "A dataset may be legally pinned to one site"
        ],
        boundaries={
            "tenant": "gravity decisions never move one tenant's data to serve another",
            "environment": "cost models differ per environment",
            "site": "each site carries a residency label and an egress cost",
            "workload": "recommendations are per workload and dataset pair"
        },
        mandatory=[
            "Cost both moving data and moving compute",
            "Eliminate options residency forbids before comparing cost",
            "Recommend nothing rather than an illegal move",
            "Account for egress asymmetry between sites",
            "Return the reasoning with every recommendation"
        ],
        optional=[
            "Partial dataset movement",
            "Cost amortisation across repeated jobs",
            "Replication as a third option"
        ],
        non_goals=[
            "Executing moves",
            "Authoring residency policy",
            "Overriding a legal pin",
            "Placing compute directly"
        ],
        interfaces={
            "datasets": "PK_DATASET/1 - dataset location, size and classification",
            "recommend": "PK_GRAVITY_RECOMMENDATION/1 - move-data, move-compute, or none, with cost",
            "cost": "PK_MOVE_COST/1 - per-direction cost breakdown"
        },
        threats=[
            "Residency bypass through a cheaper illegal option",
            "Cost model manipulation to pull data to an attacker's site",
            "Classification downgrade to unlock a destination",
            "Egress cost inflation as a denial-of-service"
        ],
        failure_modes=[
            "No legal destination for the dataset",
            "Dataset has not converged and cannot safely move",
            "Cost model missing for a site pair",
            "Compute cannot run at the data's site"
        ],
        slos=[
            Slo("legality", "zero recommendations violating residency", "no budget"),
            Slo("completeness", "every recommendation carries a full cost breakdown", "no budget"),
            Slo("decision latency", "p99 recommendation under 50ms", "1% may exceed")
        ],
        signals={
            "gravity_recommendations": "counter by direction and outcome",
            "illegal_options_eliminated": "counter by classification and site",
            "move_cost_estimate": "histogram of recommended-option cost",
            "no_legal_option": "counter of workload/dataset pairs with no legal answer"
        },
    )
