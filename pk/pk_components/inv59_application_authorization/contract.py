"""Binding contract for INV-59 - Application authorization.

Application authorization answers one question per call: may this identity perform this operation on this resource? The answer defaults to no, an explicit deny beats any allow, and every decision -- including the reason -- is recorded so a refusal can be explained and an allow can be audited.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-59"
ELEMENT_NAME = "Application authorization"


def build() -> Contract:
    """Return the production contract for INV-59."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own call-level authorization: default-deny policy evaluation, deny precedence, operation and resource matching, and an explained, auditable decision record."
        ),
        owns=[
            "Policy evaluation",
            "Default deny",
            "Deny precedence over allow",
            "Operation and resource pattern matching",
            "Decision records with reasons"
        ],
        not_owns=[
            "Identity issuance",
            "Policy authoring UX",
            "Transport security",
            "Secret storage",
            "Business rules"
        ],
        dependencies=[
            Dependency("PLN-07 Security plane", "upstream", "Issues the identities decisions are made on"),
            Dependency("GAP-13 Policy engine", "upstream", "Distributes the policy this element evaluates"),
            Dependency("INV-48 Service communication APIs", "downstream", "Asks for a decision on every call"),
            Dependency("INV-58 Existing service-mesh layer", "peer", "Supplies mapped identities from mesh certificates")
        ],
        source_of_truth="The policy version in force at decision time; each decision records which version decided it.",
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
            "Deny unless a rule allows",
            "Let any matching deny override every allow",
            "Match operations and resources precisely",
            "Record every decision with its reason and policy version",
            "Refuse to decide without an identity"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Issuing identity",
            "Authoring policy",
            "Securing transport"
        ],
        interfaces={
            "decide": "PK_AUTHZ_DECIDE/1 - identity, operation, resource to decision",
            "policy": "PK_AUTHZ_POLICY/1 - versioned allow and deny rules",
            "record": "PK_AUTHZ_RECORD/1 - decision, reason, policy version"
        },
        threats=[
            "Allow by default through a missing rule",
            "Broad allow overriding a targeted deny",
            "Anonymous calls authorized",
            "Unexplainable refusals"
        ],
        failure_modes=[
            "No identity",
            "No rule matched",
            "Explicit deny",
            "Policy unavailable"
        ],
        slos=[
            Slo("default deny", "zero allows without a matching rule", "no budget"),
            Slo("explainability", "every decision carries a reason", "no budget"),
            Slo("decision latency", "p99 under 200us", "1% may exceed")
        ],
        signals={
            "decisions": "counter by outcome",
            "denies_by_rule": "counter",
            "no_identity": "counter"
        },
    )
