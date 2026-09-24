"""Binding contract for INV-66 - Enterprise Wasm control plane.

The enterprise Wasm control plane sits above many lattices and many teams. It adds what a single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry never reaches a deployment manager.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-66"
ELEMENT_NAME = "Enterprise Wasm control plane"


def build() -> Contract:
    """Return the production contract for INV-66."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own multi-lattice governance: organisation and lattice RBAC, admission guardrails on manifests, approved registries and signers, and an append-only change audit."
        ),
        owns=[
            "Organisation and lattice RBAC",
            "Manifest admission guardrails",
            "Approved registries and signers",
            "Change audit trail",
            "Cross-lattice inventory"
        ],
        not_owns=[
            "Lattice runtime",
            "Reconciliation",
            "Signing keys",
            "Identity provider",
            "Billing"
        ],
        dependencies=[
            Dependency("INV-64 Application model", "upstream", "Supplies the manifests being admitted"),
            Dependency("GAP-13 Policy engine", "upstream", "Supplies organisation-wide policy"),
            Dependency("INV-63 Wasm deployment manager", "downstream", "Receives only admitted manifests"),
            Dependency("GAP-07 Artifact provenance/signing", "peer", "Verifies the signers guardrails require")
        ],
        source_of_truth="The audit log; the control plane's state is what the log says was admitted.",
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
            "Authorize every change by role and lattice",
            "Refuse manifests from unapproved registries",
            "Require an approved signer",
            "Record every admission and refusal",
            "Never forward an unadmitted manifest"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running lattices",
            "Holding signing keys",
            "Issuing identity"
        ],
        interfaces={
            "admit": "PK_ECP_ADMIT/1 - manifest admission decision",
            "rbac": "PK_ECP_RBAC/1 - role bindings per lattice",
            "audit": "PK_ECP_AUDIT/1 - append-only change record"
        },
        threats=[
            "Deploying from an attacker registry",
            "Developer deploying to production",
            "Audit trail rewritten after an incident"
        ],
        failure_modes=[
            "Not authorized",
            "Registry not approved",
            "Signer not approved",
            "Audit append failed"
        ],
        slos=[
            Slo("guardrails", "zero unadmitted manifests forwarded", "no budget"),
            Slo("audit integrity", "audit chain verifies end to end", "no budget"),
            Slo("admission latency", "p99 under 50ms", "1% may exceed")
        ],
        signals={
            "admissions": "counter by outcome",
            "rbac_denials": "counter",
            "audit_entries": "counter"
        },
    )
