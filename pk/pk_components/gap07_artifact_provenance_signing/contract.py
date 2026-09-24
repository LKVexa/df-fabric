"""Binding contract for GAP-07 - Artifact provenance/signing.

Artifact provenance and signing is the estate's supply-chain gate. Nothing executable or policy-bearing is consumed without a signature chaining to a trusted root, and the signature covers the artifact's digest, so swapping the bytes under a valid signature fails.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-07"
ELEMENT_NAME = "Artifact provenance/signing"


def build() -> Contract:
    """Return the production contract for GAP-07."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own artifact signing and verification: bind every executable or policy artifact to its digest and a signer in the trust store, and refuse consumption of anything unsigned, mis-signed, revoked, or digest-mismatched."
        ),
        owns=[
            "The trust store of accepted signers",
            "Artifact signing and signature format",
            "Digest binding between signature and bytes",
            "Signer revocation",
            "Provenance chain from source to deployed artifact"
        ],
        not_owns=[
            "Key custody and generation",
            "What an artifact does once admitted",
            "Node attestation",
            "Policy authorship",
            "Artifact transport"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Declares which artifact kinds require which signers"),
            Dependency("GAP-06 Device identity and attestation", "downstream", "Uses these primitives to sign attestation evidence"),
            Dependency("GAP-08 OTA lifecycle/rollback", "downstream", "Admits only signed update bundles"),
            Dependency("PLN-07 Security plane", "downstream", "Signs capability grants with these primitives"),
            Dependency("PLN-06 Data plane", "downstream", "Signs data classification labels")
        ],
        source_of_truth="The trust store: a signature verifies only against a signer currently present and unrevoked in it.",
        assumptions=[
            "Key material is held elsewhere; this element only uses and verifies",
            "A signer may be revoked after artifacts it signed were already deployed",
            "Some artifacts arrive at a disconnected site with a stale trust store"
        ],
        boundaries={
            "tenant": "tenants may have their own signers but never sign estate-wide artifacts",
            "environment": "trust stores are per environment and do not promote automatically",
            "site": "a site may hold a cached trust store with a staleness bound",
            "workload": "each workload artifact carries its own provenance chain"
        },
        mandatory=[
            "Bind every signature to the artifact's digest",
            "Verify against a signer present and unrevoked in the trust store",
            "Refuse unsigned executable or policy artifacts",
            "Reject a signature whose digest does not match the bytes",
            "Record the provenance chain for every admitted artifact"
        ],
        optional=[
            "Multi-signature thresholds for high-risk artifacts",
            "Transparency-log inclusion proofs",
            "Counter-signing by an independent reviewer"
        ],
        non_goals=[
            "Generating or storing private keys",
            "Judging artifact behaviour",
            "Attesting nodes",
            "Guaranteeing revocation reaches a partitioned site instantly"
        ],
        interfaces={
            "sign": "PK_SIGNATURE/1 - produce a digest-bound signature for an artifact",
            "verify": "PK_VERIFICATION/1 - verify a signature against the trust store",
            "trust": "PK_TRUST_STORE/1 - accepted signers, their roles, and revocations",
            "provenance": "PK_PROVENANCE/1 - the chain from source to deployed artifact"
        },
        threats=[
            "Byte substitution under a valid signature",
            "A revoked signer's old artifacts still being admitted",
            "Trust-store poisoning adding a hostile signer",
            "Signature stripping followed by unsigned admission",
            "Role confusion: a data signer signing executable code"
        ],
        failure_modes=[
            "Digest mismatch between signature and bytes",
            "Signer absent from the trust store",
            "Signer revoked after the artifact was signed",
            "Artifact kind requires a role the signer does not hold"
        ],
        slos=[
            Slo("verification soundness", "zero artifacts admitted whose digest does not match their signature", "no budget"),
            Slo("revocation", "zero artifacts admitted from a signer revoked in the local trust store", "no budget"),
            Slo("verification latency", "p99 verification under 2ms per artifact", "1% may exceed")
        ],
        signals={
            "verifications": "counter by artifact kind and outcome",
            "digest_mismatches": "counter of byte-substitution attempts caught",
            "revoked_signer_use": "counter of artifacts refused for a revoked signer",
            "trust_store_age_seconds": "gauge of local trust-store staleness",
            "unsigned_refusals": "counter of unsigned artifacts refused"
        },
    )
