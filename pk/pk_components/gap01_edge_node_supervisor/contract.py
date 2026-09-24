"""Binding contract for GAP-01 - Edge Node Supervisor.

The edge node supervisor is the single local authority on a node: it owns the node's lifecycle state machine, drains workloads before the node stops accepting them, and keeps the node honest when the control plane is unreachable. Nothing else on the node may declare it healthy.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-01"
ELEMENT_NAME = "Edge Node Supervisor"


def build() -> Contract:
    """Return the production contract for GAP-01."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the node lifecycle state machine -- joining, ready, draining, cordoned, stopped -- enforce legal transitions, and drain admitted workloads before a node leaves service."
        ),
        owns=[
            "The node lifecycle state machine and its legal transitions",
            "Local health aggregation for the node",
            "Workload drain ordering and completion",
            "Cordon and uncordon",
            "Local supervision when the control plane is unreachable"
        ],
        not_owns=[
            "Placement decisions",
            "Isolation enforcement",
            "Hardware capability discovery",
            "Control-plane membership",
            "Workload business logic"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies the capabilities this node advertises"),
            Dependency("GAP-09 Unified observability", "upstream", "Supplies the health signals aggregated into node state"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Stops placing onto a cordoned or draining node"),
            Dependency("PLN-04 Execution plane", "downstream", "Tears down tier instances as the drain proceeds"),
            Dependency("GAP-04 Disconnected-operation controller", "peer", "Takes over policy when the control plane is unreachable")
        ],
        source_of_truth="The supervisor's own state machine; a node is ready only when the supervisor says so, never because a report is absent.",
        assumptions=[
            "The control plane may be unreachable for extended periods",
            "A drain may not complete if a workload refuses to stop",
            "Health signals may be missing rather than negative"
        ],
        boundaries={
            "tenant": "drain ordering never prioritises one tenant over another except by declared class",
            "environment": "a node belongs to exactly one environment for its lifetime",
            "site": "the supervisor is the site's local authority for this node only",
            "workload": "each admitted workload is drained individually with its own deadline"
        },
        mandatory=[
            "Enforce legal lifecycle transitions and refuse illegal ones",
            "Stop accepting placements the moment a node is cordoned",
            "Drain every admitted workload before reporting stopped",
            "Escalate a drain that exceeds its deadline rather than reporting success",
            "Continue supervising when the control plane is unreachable"
        ],
        optional=[
            "Graceful workload notification before drain",
            "Drain rate limiting",
            "Automatic uncordon on recovery"
        ],
        non_goals=[
            "Deciding where drained workloads go",
            "Provisioning or decommissioning hardware",
            "Acting as a control-plane member",
            "Declaring a node healthy on missing evidence"
        ],
        interfaces={
            "lifecycle": "PK_NODE_LIFECYCLE/1 - transition requests and the resulting node state",
            "drain": "PK_DRAIN/1 - drain progress per workload with deadlines",
            "health": "PK_NODE_HEALTH/1 - aggregated local health and its contributing signals"
        },
        threats=[
            "A workload refusing to drain to pin a node in service",
            "Forged health signals keeping an unhealthy node ready",
            "Cordon bypass placing work onto a draining node",
            "Supervisor impersonation by a co-resident process"
        ],
        failure_modes=[
            "Drain deadline exceeded with workloads still resident",
            "Health signals absent for longer than the staleness bound",
            "Illegal transition requested by the control plane",
            "Control plane unreachable during a drain"
        ],
        slos=[
            Slo("transition legality", "zero illegal lifecycle transitions applied", "no budget"),
            Slo("drain completeness", "zero nodes reporting stopped with resident workloads", "no budget"),
            Slo("cordon latency", "placements stop within one scheduling interval of cordon", "1% may see one extra placement")
        ],
        signals={
            "node_state": "current lifecycle state with the reason for the last transition",
            "drain_remaining": "gauge of workloads still resident during a drain",
            "drain_deadline_breaches": "counter of workloads that outlived their drain deadline",
            "health_signal_staleness_seconds": "gauge per contributing signal",
            "illegal_transitions": "counter of refused transition requests"
        },
    )
