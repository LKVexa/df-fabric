"""Binding contract for INV-58 - Existing service-mesh layer.

The existing service-mesh layer is already doing mTLS, retries and routing for current workloads, and the new runtime has to coexist with it rather than duplicate it. The sharpest hazard is retry multiplication: three app retries through a mesh that also retries three times is nine attempts against a struggling service. This element owns the division of labour.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-58"
ELEMENT_NAME = "Existing service-mesh layer"


def build() -> Contract:
    """Return the production contract for INV-58."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own coexistence with the incumbent mesh: which layer retries, total-attempt budgets, identity handoff from mesh certificates to runtime identities, and detection of traffic bypassing the mesh."
        ),
        owns=[
            "Retry ownership between app runtime and mesh",
            "Total-attempt budgets",
            "Mesh-to-runtime identity mapping",
            "Mesh-bypass detection",
            "Migration of policies off the mesh"
        ],
        not_owns=[
            "The mesh's data plane",
            "Certificate issuance",
            "Application retry code",
            "Routing policy content",
            "Network hardware"
        ],
        dependencies=[
            Dependency("INV-48 Service communication APIs", "upstream", "The runtime's retry policy to be reconciled"),
            Dependency("PLN-07 Security plane", "upstream", "Issues the identities the mesh certificates carry"),
            Dependency("INV-59 Application authorization", "downstream", "Consumes the mapped identity"),
            Dependency("GAP-09 Unified observability", "peer", "Sees both layers' retries in one trace")
        ],
        source_of_truth="The effective policy after reconciliation; neither layer's own configuration alone says how many attempts a call gets.",
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
            "Give retries to exactly one layer per route",
            "Cap total attempts per call",
            "Map mesh certificate identity to a runtime identity",
            "Flag traffic that bypasses the mesh",
            "Migrate policies route by route"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running the mesh",
            "Issuing certificates",
            "Writing app retry code"
        ],
        interfaces={
            "reconcile": "PK_MESH_RECONCILE/1 - effective retry ownership per route",
            "identity": "PK_MESH_IDENTITY/1 - certificate SAN to runtime identity",
            "bypass": "PK_MESH_BYPASS/1 - a flow observed outside the mesh"
        },
        threats=[
            "Retry storm from multiplied retries",
            "Identity lost at the layer boundary",
            "Workload quietly bypassing mTLS"
        ],
        failure_modes=[
            "Budget exceeded",
            "Identity unmappable",
            "Bypass detected",
            "Conflicting policies"
        ],
        slos=[
            Slo("bounded attempts", "no call exceeds its total-attempt budget", "no budget"),
            Slo("no bypass", "every bypass flow flagged within one scrape", "no budget"),
            Slo("handoff cost", "p99 identity mapping under 100us", "1% may exceed")
        ],
        signals={
            "effective_attempts": "histogram by route",
            "bypass_flows": "counter",
            "identity_unmapped": "counter"
        },
    )
