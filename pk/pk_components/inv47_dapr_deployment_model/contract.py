"""Binding contract for INV-47 - Dapr deployment model.

The deployment model decides where the application runtime lives relative to the application: a sidecar beside each instance, one shared agent per node, or embedded in-process. Each trades isolation against density, and the model's job is to make that trade explicit, give every application exactly one reachable runtime, and keep the runtime within a supported version of its control plane.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-47"
ELEMENT_NAME = "Dapr deployment model"


def build() -> Contract:
    """Return the production contract for INV-47."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own runtime placement relative to applications: mode selection, one-runtime-per-instance binding, control-plane version-skew bounds, and the isolation consequences of each mode."
        ),
        owns=[
            "Deployment mode selection (sidecar, per-node, embedded)",
            "Binding each app instance to exactly one runtime",
            "Version-skew bounds against the control plane",
            "Mode-specific isolation guarantees",
            "Runtime lifecycle tied to the application's"
        ],
        not_owns=[
            "Building-block behaviour",
            "Scheduling of application instances",
            "Networking",
            "Image build",
            "Authorization"
        ],
        dependencies=[
            Dependency("INV-46 Distributed application runtime", "upstream", "The runtime being deployed"),
            Dependency("SCH-01 Multi-runtime scheduler", "upstream", "Places the application instances"),
            Dependency("INV-48 Service communication APIs", "downstream", "Assumes a reachable local runtime"),
            Dependency("GAP-08 OTA lifecycle/rollback", "peer", "Rolls runtime versions within the skew bound")
        ],
        source_of_truth="The binding table from application instance to runtime; a runtime that is not bound serves nothing.",
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
            "Bind every application instance to exactly one runtime",
            "Refuse a mode that breaks the tenant's isolation class",
            "Refuse a runtime outside the supported skew",
            "Start the runtime before the application is ready",
            "Stop the runtime with its application"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing building blocks",
            "Scheduling instances",
            "Building images"
        ],
        interfaces={
            "mode": "PK_DEPLOY_MODE/1 - sidecar, per-node or embedded",
            "bind": "PK_DEPLOY_BIND/1 - instance-to-runtime binding",
            "skew": "PK_DEPLOY_SKEW/1 - runtime and control-plane versions"
        },
        threats=[
            "Shared per-node runtime serving two tenants",
            "Orphaned runtime outliving its application",
            "Runtime too old for the control plane's API"
        ],
        failure_modes=[
            "No runtime reachable",
            "Two runtimes bound to one instance",
            "Version skew exceeded",
            "Mode disallowed"
        ],
        slos=[
            Slo("binding", "every ready instance has exactly one runtime", "no budget"),
            Slo("skew", "zero runtimes more than one minor version behind", "no budget"),
            Slo("startup", "p99 runtime ready within 500ms of instance start", "1% may exceed")
        ],
        signals={
            "bound_instances": "gauge by mode",
            "skew_refusals": "counter",
            "orphans": "gauge",
            "startup_ms": "histogram"
        },
    )
