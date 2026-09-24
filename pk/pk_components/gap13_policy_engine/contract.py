"""Binding contract for GAP-13 - Policy engine.

The policy engine is where the estate's rules are evaluated rather than scattered. Decisions default to deny, the most specific matching rule wins with deterministic tie-breaking, and every verdict carries the rule that produced it -- so an operator can always answer why.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-13"
ELEMENT_NAME = "Policy engine"


def build() -> Contract:
    """Return the production contract for GAP-13."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own policy evaluation for the estate: evaluate a request against versioned rules, default to deny, and return an explainable verdict naming the deciding rule and the policy version it came from."
        ),
        owns=[
            "Rule representation and specificity ordering",
            "Deny-by-default evaluation",
            "Deterministic tie-breaking between equally specific rules",
            "Verdict explanation",
            "Policy versioning and staleness"
        ],
        not_owns=[
            "Policy authorship",
            "Enforcement at the call site",
            "Identity or attestation",
            "Signing the policy bundle",
            "What a caller does with a verdict"
        ],
        dependencies=[
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies the signed policy bundle before it is loaded"),
            Dependency("PLN-01 Intent plane", "downstream", "Admits declarations on these verdicts"),
            Dependency("PLN-06 Data plane", "downstream", "Takes residency rules from here"),
            Dependency("GAP-04 Disconnected-operation controller", "downstream", "Caches these rules for offline evaluation"),
            Dependency("PLN-07 Security plane", "peer", "Asks whether a requested grant is permitted")
        ],
        source_of_truth="The loaded, signature-verified policy bundle and its version; an unverified bundle is never loaded.",
        assumptions=[
            "Rules conflict and the conflict must resolve deterministically",
            "A cached bundle at a disconnected site goes stale",
            "A request may name attributes no rule mentions"
        ],
        boundaries={
            "tenant": "tenant rules may narrow estate rules, never widen them",
            "environment": "each environment loads its own bundle",
            "site": "a site evaluates against its cached bundle and reports its staleness",
            "workload": "requests carry the workload as an evaluable attribute"
        },
        mandatory=[
            "Deny any request no rule permits",
            "Prefer the most specific matching rule",
            "Break specificity ties deterministically and record that it happened",
            "Return the deciding rule and policy version with every verdict",
            "Refuse to load a bundle that fails verification"
        ],
        optional=[
            "Rule simulation against historical requests",
            "Policy linting for unreachable rules",
            "Per-rule metrics"
        ],
        non_goals=[
            "Authoring rules",
            "Enforcing verdicts",
            "Widening a tenant's authority",
            "Evaluating against an unverified bundle"
        ],
        interfaces={
            "load": "PK_POLICY_BUNDLE/1 - a signed, versioned rule set",
            "evaluate": "PK_POLICY_VERDICT/1 - allow or deny with the deciding rule",
            "explain": "PK_POLICY_EXPLANATION/1 - every rule that matched and why one won"
        },
        threats=[
            "An unsigned bundle introducing a permissive rule",
            "Tenant rules widening estate authority",
            "Attribute injection matching an over-broad rule",
            "Stale cached policy permitting something since revoked",
            "Tie-break manipulation to select an attacker's rule"
        ],
        failure_modes=[
            "No rule matches the request",
            "Two equally specific rules disagree",
            "Bundle fails signature verification",
            "Cached bundle exceeds its staleness bound"
        ],
        slos=[
            Slo("deny by default", "zero requests allowed without a matching allow rule", "no budget"),
            Slo("determinism", "identical request and bundle produce an identical verdict", "no budget"),
            Slo("explainability", "100% of verdicts name their deciding rule and policy version", "no budget")
        ],
        signals={
            "policy_verdicts": "counter by effect, rule and tenant",
            "default_denies": "counter of requests matched by no rule",
            "specificity_ties": "counter of verdicts decided by tie-break",
            "bundle_version": "current loaded policy version",
            "bundle_age_seconds": "gauge of cached-bundle staleness"
        },
    )
