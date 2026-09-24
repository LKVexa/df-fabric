"""Binding contract for INV-64 - Application model.

The application model is the declarative description of an application: its components, the providers they link to, and the traits -- scaling, spread -- attached to each. Its value is validation before anything runs: a link to a component that does not exist, a trait on a component that is not there, or a schema version the platform does not speak is refused at submit.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-64"
ELEMENT_NAME = "Application model"


def build() -> Contract:
    """Return the production contract for INV-64."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the application manifest: schema versioning, component and provider declarations, link and trait validation, and a canonical form for diffing and signing."
        ),
        owns=[
            "Manifest schema and versions",
            "Component and provider declarations",
            "Link validation",
            "Trait validation",
            "Canonical manifest form"
        ],
        not_owns=[
            "Running applications",
            "Reconciliation",
            "Provider implementations",
            "Artifact storage",
            "Policy decisions"
        ],
        dependencies=[
            Dependency("INV-10 Component composition system", "upstream", "Defines what a component reference is"),
            Dependency("INV-63 Wasm deployment manager", "downstream", "Deploys validated manifests"),
            Dependency("INV-66 Enterprise Wasm control plane", "downstream", "Applies guardrails to manifests"),
            Dependency("INV-65 Capability providers", "peer", "The providers a manifest links to")
        ],
        source_of_truth="The canonical manifest; any two manifests with the same canonical form are the same application.",
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
            "Refuse unsupported schema versions",
            "Refuse links to undeclared components or providers",
            "Refuse traits on undeclared components",
            "Produce a canonical form",
            "Report every validation error at once"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running anything",
            "Reconciling",
            "Implementing providers"
        ],
        interfaces={
            "manifest": "PK_APP_MANIFEST/1 - components, providers, links, traits",
            "validate": "PK_APP_VALIDATE/1 - all validation errors",
            "canonical": "PK_APP_CANONICAL/1 - the canonical digest"
        },
        threats=[
            "Dangling link discovered only at run time",
            "Two equivalent manifests treated as different",
            "Unknown schema silently interpreted"
        ],
        failure_modes=[
            "Schema unsupported",
            "Dangling link",
            "Orphan trait",
            "Duplicate name"
        ],
        slos=[
            Slo("fail at submit", "zero dangling links reach deployment", "no budget"),
            Slo("canonical identity", "equivalent manifests share one digest", "no budget"),
            Slo("validation time", "p99 under 5ms", "1% may exceed")
        ],
        signals={
            "submitted": "counter",
            "rejected": "counter by error",
            "canonical_collisions": "counter"
        },
    )
