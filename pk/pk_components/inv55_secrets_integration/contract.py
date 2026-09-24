"""Binding contract for INV-55 - Secrets integration.

Secrets integration lets an application reference a secret by name and get its value at run time without the value ever sitting in configuration, logs or the application's image. Access is scoped per application and per secret, values arrive with a version and a lease, and rotation is a new version rather than an overwrite.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-55"
ELEMENT_NAME = "Secrets integration"


def build() -> Contract:
    """Return the production contract for INV-55."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own secret resolution for applications: reference-by-name, per-application scoping, versioned rotation, leased access and redaction of values from every log and error."
        ),
        owns=[
            "Secret references in configuration",
            "Per-application, per-secret access scoping",
            "Versioned rotation",
            "Leased (time-bounded) access",
            "Redaction of secret values"
        ],
        not_owns=[
            "Secret storage backends",
            "Key custody and HSMs",
            "Identity issuance",
            "Application logic",
            "Audit storage"
        ],
        dependencies=[
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Shares the estate's key-custody boundary"),
            Dependency("INV-46 Distributed application runtime", "upstream", "Exposes secrets as a building block"),
            Dependency("INV-49 Pluggable infrastructure adapters", "downstream", "Admits secret-store backends"),
            Dependency("INV-59 Application authorization", "peer", "Authorizes who may resolve which secret")
        ],
        source_of_truth="The secret store's current version; an application's copy is valid only while its lease is.",
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
            "Reference secrets by name, never embed values",
            "Scope access per application and secret",
            "Rotate by adding a version",
            "Expire access at lease end",
            "Redact values everywhere they could leak"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Storing secrets",
            "Holding root keys",
            "Issuing identities"
        ],
        interfaces={
            "resolve": "PK_SECRET_RESOLVE/1 - name to leased, versioned value",
            "rotate": "PK_SECRET_ROTATE/1 - add a new version",
            "scope": "PK_SECRET_SCOPE/1 - which apps may resolve which secrets"
        },
        threats=[
            "Secret value written to a log",
            "Application reading another's secret",
            "Leaked value usable forever",
            "Rotation breaking running apps"
        ],
        failure_modes=[
            "Secret not found",
            "Access denied",
            "Lease expired",
            "Version retired"
        ],
        slos=[
            Slo("no leakage", "zero secret values in logs or errors", "no budget"),
            Slo("scoping", "zero resolutions outside scope", "no budget"),
            Slo("resolution latency", "p99 under 5ms from cache", "1% may exceed")
        ],
        signals={
            "resolutions": "counter by secret",
            "denials": "counter",
            "rotations": "counter",
            "lease_expiries": "counter"
        },
    )
