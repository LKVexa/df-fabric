"""Binding contract for INV-63 - Wasm deployment manager.

The Wasm deployment manager holds desired state -- which components, how many, spread across which labels -- and reconciles the lattice toward it. Its guarantees are convergence (repeated reconciliation reaches the desired state and then does nothing) and safe rollout (never more than the allowed number of instances unavailable while a version changes).
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-63"
ELEMENT_NAME = "Wasm deployment manager"


def build() -> Contract:
    """Return the production contract for INV-63."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own declarative deployment: desired-state storage, reconciliation diffs, spread constraints, idempotent convergence and bounded-unavailability rollouts."
        ),
        owns=[
            "Desired-state storage",
            "Reconciliation diff computation",
            "Spread across host labels",
            "Idempotent convergence",
            "Rolling updates with a max-unavailable bound"
        ],
        not_owns=[
            "The application manifest format",
            "Running components",
            "Artifact signing",
            "Host provisioning",
            "Provider implementations"
        ],
        dependencies=[
            Dependency("INV-64 Application model", "upstream", "Supplies validated manifests"),
            Dependency("INV-60 Wasm application fabric", "downstream", "Starts and stops what this manager decides"),
            Dependency("INV-66 Enterprise Wasm control plane", "downstream", "Manages many of these managers"),
            Dependency("GAP-08 OTA lifecycle/rollback", "peer", "Supplies rollback for failed rollouts")
        ],
        source_of_truth="The desired-state record; the lattice's actual state is observed and corrected toward it.",
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
            "Compute the minimal diff to desired state",
            "Honour spread constraints",
            "Do nothing when actual equals desired",
            "Bound unavailability during rollout",
            "Record every reconciliation action"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Defining manifests",
            "Running components",
            "Provisioning hosts"
        ],
        interfaces={
            "desired": "PK_DEPLOY_DESIRED/1 - component, version, count, spread",
            "diff": "PK_DEPLOY_DIFF/1 - start and stop actions",
            "rollout": "PK_DEPLOY_ROLLOUT/1 - batched update plan"
        },
        threats=[
            "Reconciliation flapping",
            "Rollout taking all replicas down at once",
            "Spread collapsing onto one zone"
        ],
        failure_modes=[
            "Insufficient hosts for spread",
            "Start failed",
            "Rollout stalled",
            "Desired state invalid"
        ],
        slos=[
            Slo("convergence", "a second reconcile after convergence emits zero actions", "no budget"),
            Slo("availability", "never more than max-unavailable instances down in rollout", "no budget"),
            Slo("reconcile time", "p99 diff under 10ms for 1000 instances", "1% may exceed")
        ],
        signals={
            "reconciles": "counter",
            "actions": "counter by kind",
            "rollout_batches": "counter"
        },
    )
