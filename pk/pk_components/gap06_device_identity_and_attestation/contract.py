"""Binding contract for GAP-06 - Device identity and attestation.

Device identity and attestation is where trust actually starts. A node proves what it is with evidence rooted in hardware, that evidence expires, and a node whose measurements drifted from the accepted set is untrusted even if it was trusted a minute ago.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-06"
ELEMENT_NAME = "Device identity and attestation"


def build() -> Contract:
    """Return the production contract for GAP-06."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own node identity and the attestation lifecycle: bind each node to a hardware-rooted identity, verify its measurements against an accepted set, and expire the verdict so trust is continuously re-earned rather than granted once."
        ),
        owns=[
            "Node identity binding to a hardware root",
            "Attestation evidence verification",
            "The accepted measurement set and its versioning",
            "Attestation verdict expiry",
            "Quarantine of nodes whose measurements drifted"
        ],
        not_owns=[
            "Capability probing",
            "Artifact signing",
            "Policy authorship",
            "Node lifecycle",
            "Grant issuance"
        ],
        dependencies=[
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Supplies the signing primitives and trust store"),
            Dependency("PLN-07 Security plane", "downstream", "Issues capability grants only to attested identities"),
            Dependency("GAP-02 Hardware capability discovery", "downstream", "Signs its capability report with this identity"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Excludes unattested nodes from candidacy"),
            Dependency("GAP-01 Edge Node Supervisor", "peer", "Cannot report ready without a valid attestation verdict")
        ],
        source_of_truth="The attestation verdict, valid only until its expiry; absence of a verdict is untrusted, never trusted-by-default.",
        assumptions=[
            "Some nodes have no hardware root of trust and can never be fully attested",
            "The accepted measurement set changes as firmware and kernels are updated",
            "Evidence may arrive late from a disconnected site"
        ],
        boundaries={
            "tenant": "node identity is estate-level, never tenant-scoped",
            "environment": "each environment carries its own accepted measurement set",
            "site": "a site may hold nodes at different attestation levels",
            "workload": "workload trust classes are matched against node attestation level"
        },
        mandatory=[
            "Bind each node identity to a hardware root where one exists",
            "Verify measurements against the environment's accepted set",
            "Expire every verdict and require re-attestation",
            "Treat a missing or expired verdict as untrusted",
            "Quarantine a node whose measurements left the accepted set"
        ],
        optional=[
            "Remote attestation service integration",
            "Measurement allow-list staging for firmware rollouts",
            "Attestation level downgrade instead of quarantine"
        ],
        non_goals=[
            "Granting capabilities",
            "Signing artifacts",
            "Probing hardware capability",
            "Trusting a node because it was trusted previously"
        ],
        interfaces={
            "enrol": "PK_NODE_IDENTITY/1 - bind a node to a hardware-rooted identity",
            "attest": "PK_ATTESTATION/1 - submit evidence and receive a verdict with expiry",
            "measurements": "PK_ACCEPTED_MEASUREMENTS/1 - the environment's accepted measurement set"
        },
        threats=[
            "Evidence replay from a previously healthy boot",
            "A node without a hardware root claiming full attestation",
            "Measurement set poisoning to accept a compromised image",
            "Verdict reuse past expiry",
            "Identity cloning across nodes"
        ],
        failure_modes=[
            "Evidence nonce does not match the challenge",
            "Measurements absent from the accepted set",
            "No hardware root available on this node",
            "Verdict expired while the site was partitioned"
        ],
        slos=[
            Slo("verdict soundness", "zero attested verdicts for measurements outside the accepted set", "no budget"),
            Slo("replay resistance", "zero verdicts issued for evidence reusing a spent nonce", "no budget"),
            Slo("re-attestation", "99.9% of nodes re-attest before their verdict expires", "0.1% fall to untrusted and are cordoned")
        ],
        signals={
            "attestation_verdicts": "counter by level and outcome",
            "verdict_remaining_seconds": "gauge of time until each node's verdict expires",
            "quarantined_nodes": "gauge of nodes outside the accepted measurement set",
            "replay_rejections": "counter of evidence refused for a spent nonce"
        },
    )
