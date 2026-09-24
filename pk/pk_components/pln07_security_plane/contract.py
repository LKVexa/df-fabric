"""Binding contract for PLN-07 - Security plane.

The security plane replaces ambient trust with explicit, attenuable capabilities. Nothing in the estate holds authority it was not granted; every grant names its holder, its scope, and its expiry, and any holder may attenuate a grant but never widen one.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-07"
ELEMENT_NAME = "Security plane"


def build() -> Contract:
    """Return the production contract for PLN-07."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own capability issuance, attenuation, and verification for the estate: every authority is an explicit, scoped, expiring grant, and no path exists to widen a grant after issue."
        ),
        owns=[
            "Capability grant issuance and format",
            "Attenuation semantics",
            "Grant verification and expiry",
            "Trust-class definitions",
            "Revocation and the revocation horizon"
        ],
        not_owns=[
            "Identity provisioning",
            "Hardware attestation roots",
            "Policy authorship",
            "Enforcement points in other planes",
            "Secret material storage"
        ],
        dependencies=[
            Dependency("GAP-06 Device identity and attestation", "upstream", "Supplies the identity a grant is issued to"),
            Dependency("GAP-13 Policy engine", "upstream", "Decides whether a requested grant is permitted"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads against the trust classes defined here"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Enforces capability grants at every call"),
            Dependency("PLN-01 Intent plane", "peer", "Admits declarations against grants issued here")
        ],
        source_of_truth="The issued grant itself, verified by signature chain; no registry lookup may widen it.",
        assumptions=[
            "Clock skew between issuer and verifier is bounded and known",
            "Revocation propagation is not instantaneous, so grants must be short-lived",
            "A holder may be compromised, so attenuation must be one-way"
        ],
        boundaries={
            "tenant": "a grant names exactly one tenant and cannot be attenuated across tenants",
            "environment": "grants are environment-scoped and do not promote",
            "site": "a grant may be site-restricted but never site-widened",
            "workload": "the workload identity is part of the grant subject"
        },
        mandatory=[
            "Issue grants with an explicit subject, scope, and expiry",
            "Verify signature, expiry, and scope on every use",
            "Permit attenuation and refuse widening",
            "Reject a grant whose chain contains an expired or revoked link",
            "Define the trust classes other planes admit against"
        ],
        optional=[
            "Offline verification caches for disconnected sites",
            "Grant delegation depth limits beyond the default",
            "Hardware-bound grant holders"
        ],
        non_goals=[
            "Provisioning identities",
            "Storing secrets",
            "Enforcing grants on behalf of other planes",
            "Instantaneous revocation"
        ],
        interfaces={
            "issue": "PK_GRANT/1 - issue a scoped, expiring capability grant",
            "attenuate": "PK_GRANT/1 - derive a strictly narrower grant from a held one",
            "verify": "PK_GRANT_VERIFICATION/1 - verify a grant chain at a point in time",
            "revoke": "PK_REVOCATION/1 - publish a revocation with its horizon"
        },
        threats=[
            "A holder attempting to widen its own grant",
            "Replay of an expired grant against a skewed verifier",
            "Chain splicing to inherit a sibling's scope",
            "Revocation suppression at a disconnected site",
            "Confused deputy: a trusted plane acting on an attenuated caller's behalf with its own authority"
        ],
        failure_modes=[
            "Grant expired at the point of use",
            "A link in the chain is revoked",
            "Requested attenuation is not a subset of the held scope",
            "Delegation depth exceeded"
        ],
        slos=[
            Slo("widening", "zero grants verified whose scope exceeds their parent", "no budget"),
            Slo("expiry", "zero expired grants accepted outside the declared skew allowance", "no budget"),
            Slo("verification latency", "p99 chain verification under 1ms for depth 5", "1% may exceed")
        ],
        signals={
            "grants_issued": "counter by tenant, scope size, and lifetime",
            "verification_failures": "counter by reason (expired, revoked, widened, depth)",
            "attenuations": "counter of derived grants by depth",
            "revocations": "counter with propagation horizon"
        },
    )
