"""Binding contract for INV-67 - Kubernetes integration mechanism.

The Kubernetes integration mechanism lets existing manifests and tooling drive the new runtime during migration. It translates the supported subset of a pod spec into a runtime placement request -- and is loud about the rest: a privileged container or a hostPath mount is refused with the field named, never silently dropped into a workload that then behaves differently.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-67"
ELEMENT_NAME = "Kubernetes integration mechanism"


def build() -> Contract:
    """Return the production contract for INV-67."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the Kubernetes bridge: pod-spec translation, explicit refusal of unsupported fields, label and resource mapping, and status projected back into Kubernetes terms."
        ),
        owns=[
            "Pod-spec subset translation",
            "Explicit refusal of unsupported fields",
            "Label and annotation mapping",
            "Resource request mapping",
            "Status projection back to Kubernetes"
        ],
        not_owns=[
            "The Kubernetes API server",
            "Runtime placement decisions",
            "Image building",
            "Cluster networking",
            "Operators"
        ],
        dependencies=[
            Dependency("SCH-01 Multi-runtime scheduler", "downstream", "Receives the translated placement requests"),
            Dependency("PLN-02 Application plane", "upstream", "Owns the application identity the pod maps onto"),
            Dependency("INV-68 Resource packing", "downstream", "Packs the translated resource requests"),
            Dependency("GAP-15 Runtime compatibility certification", "peer", "Certifies which pod features are supported")
        ],
        source_of_truth="The translated placement request; what Kubernetes asked for is honoured only as far as the translation says.",
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
            "Translate every supported pod field",
            "Refuse unsupported fields by name",
            "Map requests and limits exactly",
            "Preserve labels for selection",
            "Project runtime status back as pod phases"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running an API server",
            "Deciding placement",
            "Building images"
        ],
        interfaces={
            "translate": "PK_K8S_TRANSLATE/1 - pod spec to placement request",
            "refuse": "PK_K8S_REFUSE/1 - unsupported fields named",
            "status": "PK_K8S_STATUS/1 - runtime state as pod phase"
        },
        threats=[
            "Privileged workload silently run unprivileged or vice versa",
            "Host mounts ignored",
            "Resource limits lost in translation"
        ],
        failure_modes=[
            "Unsupported field",
            "Invalid quantity",
            "Image unresolvable",
            "Status unknown"
        ],
        slos=[
            Slo("no silent drops", "every unsupported field refused by name", "no budget"),
            Slo("fidelity", "requests and limits preserved exactly", "no budget"),
            Slo("translation time", "p99 under 5ms", "1% may exceed")
        ],
        signals={
            "translated": "counter",
            "refused": "counter by field",
            "status_syncs": "counter"
        },
    )
