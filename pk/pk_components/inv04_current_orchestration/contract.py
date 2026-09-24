"""Binding contract for INV-04 - Current orchestration.

Current orchestration is the scheduler the estate uses today: desired replica counts, reconciliation, and node drains for maintenance. The new platform has to coexist with it and eventually take over, so its behaviour is modelled exactly -- including the rule that a drain must never take a service below its disruption budget.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-04"
ELEMENT_NAME = "Current orchestration"


def build() -> Contract:
    """Return the production contract for INV-04."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the model of the incumbent orchestrator: replica reconciliation, node drain with disruption budgets, and the hand-off surface to the new scheduler."
        ),
        owns=[
            "Replica reconciliation model",
            "Node drain procedure",
            "Disruption budget enforcement",
            "Workload inventory for hand-off",
            "Behavioural parity checks against the new scheduler"
        ],
        not_owns=[
            "Cluster provisioning",
            "The API server",
            "Networking",
            "Image building",
            "New-platform scheduling"
        ],
        dependencies=[
            Dependency("INV-02 Container substrate", "upstream", "Supplies images the orchestrator runs"),
            Dependency("INV-03 Container hardening", "upstream", "Admits only hardened workloads"),
            Dependency("INV-67 Kubernetes integration mechanism", "downstream", "Bridges these workloads to the new runtime"),
            Dependency("SCH-01 Multi-runtime scheduler", "peer", "Must reproduce this behaviour to take over")
        ],
        source_of_truth="The desired replica count; running pods are corrected toward it, never the other way round.",
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
            "Reconcile running replicas to the desired count",
            "Honour disruption budgets on every drain",
            "Refuse a drain that would breach a budget",
            "Reschedule evicted replicas elsewhere",
            "Expose workload inventory for hand-off"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Provisioning clusters",
            "Running the API server",
            "Scheduling on the new platform"
        ],
        interfaces={
            "reconcile": "PK_ORCH_RECONCILE/1 - desired versus running",
            "drain": "PK_ORCH_DRAIN/1 - a budget-respecting node drain",
            "inventory": "PK_ORCH_INVENTORY/1 - workloads for hand-off"
        },
        threats=[
            "Maintenance drain causing an outage",
            "Replica drift unnoticed",
            "Hand-off losing workloads"
        ],
        failure_modes=[
            "Budget would be breached",
            "No capacity to reschedule",
            "Node unreachable",
            "Reconcile stalled"
        ],
        slos=[
            Slo("availability", "zero drains that breach a disruption budget", "no budget"),
            Slo("convergence", "replicas match desired within 30s", "1% may exceed"),
            Slo("inventory completeness", "every running workload listed for hand-off", "no budget")
        ],
        signals={
            "replicas": "gauge by workload",
            "drains": "counter by outcome",
            "budget_blocks": "counter"
        },
    )
