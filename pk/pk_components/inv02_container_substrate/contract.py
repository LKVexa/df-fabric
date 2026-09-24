"""Binding contract for INV-02 - Container substrate.

The container substrate is the packaging layer the estate runs on today: images made of layers, pulled by name, run by a runtime. The weakness is the name -- a tag can be moved to point at different bytes. This element resolves every image to a content digest, checks the manifest against its layers, and refuses mutable tags wherever reproducibility matters.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-02"
ELEMENT_NAME = "Container substrate"


def build() -> Contract:
    """Return the production contract for INV-02."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own image identity and integrity: digest resolution, manifest and layer verification, tag-mutability policy by environment and layer de-duplication."
        ),
        owns=[
            "Tag-to-digest resolution",
            "Manifest verification against layer digests",
            "Mutable-tag policy",
            "Layer de-duplication",
            "Image provenance records"
        ],
        not_owns=[
            "Image building",
            "Runtime execution",
            "Hardening policy",
            "Registry operation",
            "Signing keys"
        ],
        dependencies=[
            Dependency("INV-01 Legacy infrastructure substrate", "upstream", "Hands over workloads to containerise"),
            Dependency("INV-03 Container hardening", "downstream", "Hardens the images this layer identifies"),
            Dependency("GAP-07 Artifact provenance/signing", "peer", "Signs the digests this layer resolves"),
            Dependency("INV-04 Current orchestration", "downstream", "Runs images by digest")
        ],
        source_of_truth="The manifest digest; a tag is a pointer that can move, a digest is the image.",
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
            "Resolve every image reference to a digest",
            "Verify every layer against its manifest digest",
            "Refuse mutable tags in production",
            "Store shared layers once",
            "Record which digest a tag resolved to"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Building images",
            "Running containers",
            "Operating registries"
        ],
        interfaces={
            "resolve": "PK_IMAGE_RESOLVE/1 - reference to digest",
            "verify": "PK_IMAGE_VERIFY/1 - manifest and layer verification",
            "policy": "PK_IMAGE_TAGPOLICY/1 - where mutable tags are allowed"
        },
        threats=[
            "Tag moved to malicious image",
            "Layer corrupted in the registry",
            "Production running :latest"
        ],
        failure_modes=[
            "Digest mismatch",
            "Tag unresolvable",
            "Mutable tag refused",
            "Layer missing"
        ],
        slos=[
            Slo("integrity", "zero images run whose layers fail verification", "no budget"),
            Slo("reproducibility", "zero production workloads referenced by mutable tag", "no budget"),
            Slo("pull efficiency", "shared layers stored once", "no budget")
        ],
        signals={
            "pulls": "counter",
            "digest_failures": "counter",
            "tag_refusals": "counter",
            "layer_bytes_saved": "counter"
        },
    )
