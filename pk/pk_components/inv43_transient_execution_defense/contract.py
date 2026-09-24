"""Binding contract for INV-43 - Transient-execution defense.

Transient-execution defense is the tax every isolation boundary pays after Spectre. Mitigations are not free and not universal, so the honest position is a per-node record of which are active, what they cost, and which trust classes may not be co-located without them.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-43"
ELEMENT_NAME = "Transient-execution defense"


def build() -> Contract:
    """Return the production contract for INV-43."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own transient-execution mitigation state: record which mitigations are active on each node with their measured cost, and refuse co-tenancy of mutually distrusting workloads on a node whose required mitigations are absent."
        ),
        owns=[
            "Per-node mitigation inventory and its status",
            "Measured cost of each active mitigation",
            "Co-tenancy rules derived from mitigation state",
            "Sibling-thread policy",
            "Refusal of co-location when required mitigations are missing"
        ],
        not_owns=[
            "Microcode",
            "Kernel mitigation implementation",
            "Placement decisions",
            "CPU procurement",
            "Isolation tiers"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports microcode and kernel mitigation availability"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Filters co-tenancy on this element's verdict"),
            Dependency("INV-34 Legacy CPU expansion path", "peer", "Mitigations mask CPU features this element accounts for"),
            Dependency("PLN-04 Execution plane", "downstream", "Tier choice changes which mitigations are required")
        ],
        source_of_truth="The node's read-back mitigation status; an unmitigated node is unmitigated whatever the CPU generation suggests.",
        assumptions=[
            "Mitigations cost measurable performance and some are disabled for that reason",
            "SMT siblings share microarchitectural state",
            "New transient-execution classes will keep appearing"
        ],
        boundaries={
            "tenant": "co-tenancy rules are exactly about crossing tenant boundaries",
            "environment": "required mitigation sets differ per environment",
            "site": "sites differ in microcode level",
            "workload": "trust class decides which mitigations a workload requires"
        },
        mandatory=[
            "Record each mitigation's status as read back from the node",
            "Record the measured cost of each active mitigation",
            "Require core scheduling or SMT-off for cross-tenant co-tenancy",
            "Refuse co-location when a required mitigation is inactive",
            "Treat an unknown mitigation as inactive"
        ],
        optional=[
            "Per-workload mitigation opt-in above the baseline",
            "Automatic SMT disable under policy",
            "Cost-aware mitigation selection"
        ],
        non_goals=[
            "Implementing mitigations",
            "Applying microcode",
            "Claiming a mitigation the node does not report",
            "Deciding placement"
        ],
        interfaces={
            "status": "PK_MITIGATIONS/1 - active mitigations, status and measured cost",
            "cotenancy": "PK_COTENANCY/1 - whether two workloads may share this node"
        },
        threats=[
            "Cross-tenant leakage through shared microarchitectural state",
            "SMT siblings leaking across a tenant boundary",
            "Mitigations disabled for performance without a policy record",
            "A new attack class assumed covered by existing mitigations"
        ],
        failure_modes=[
            "Required mitigation inactive",
            "SMT enabled without core scheduling",
            "Mitigation status unknown",
            "Measured cost exceeds the workload's budget"
        ],
        slos=[
            Slo("co-tenancy", "zero cross-tenant co-locations without the required mitigations", "no budget"),
            Slo("status honesty", "zero mitigations reported active without a read-back", "no budget"),
            Slo("cost visibility", "100% of active mitigations carry a measured cost", "no budget")
        ],
        signals={
            "mitigation_status": "per mitigation: active, inactive or unknown",
            "mitigation_cost_percent": "gauge of measured overhead per mitigation",
            "cotenancy_refusals": "counter by missing mitigation",
            "smt_enabled_nodes": "gauge of nodes with SMT on and no core scheduling"
        },
    )
