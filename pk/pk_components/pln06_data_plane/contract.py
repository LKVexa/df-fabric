"""Binding contract for PLN-06 - Data plane.

The data plane separates control traffic from bulk movement and keeps data where gravity puts it. It admits a transfer only when the destination is a legal residence for the data's classification, and it picks a transport by payload size and locality rather than routing everything through the control path.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-06"
ELEMENT_NAME = "Data plane"


def build() -> Contract:
    """Return the production contract for PLN-06."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own bulk data movement: classify each transfer, refuse destinations that violate residency, select a transport tier by size and locality, and keep control traffic off the bulk path."
        ),
        owns=[
            "Transport tier selection for bulk payloads",
            "Data-residency admission for transfers",
            "Separation of control and bulk paths",
            "Backpressure on the bulk path",
            "Transfer integrity digests"
        ],
        not_owns=[
            "Storage backends",
            "Data classification policy authorship",
            "Control-plane messaging",
            "Encryption key custody",
            "Where a workload runs"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Supplies residency and classification policy"),
            Dependency("GAP-14 Data-gravity manager", "upstream", "Supplies locality and gravity hints"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Hands off payloads that exceed the inline limit"),
            Dependency("INV-37 Bulk data plane", "peer", "Supplies the concrete bulk transport"),
            Dependency("INV-36 Control transport", "peer", "Carries the control messages this plane must not use for bulk")
        ],
        source_of_truth="The residency policy from the policy engine; locality hints are advisory and never override it.",
        assumptions=[
            "A site may be legally barred from holding a classification regardless of capacity",
            "Kernel-bypass transport is available on some nodes and absent on others",
            "Small payloads are cheaper inline than through a bulk transfer set-up"
        ],
        boundaries={
            "tenant": "transfers are tenant-scoped; no shared bulk buffers across tenants",
            "environment": "residency policy is per environment",
            "site": "a site carries a residency label that admission is evaluated against",
            "workload": "a transfer is attributed to the originating workload"
        },
        mandatory=[
            "Refuse a transfer whose destination site may not hold the classification",
            "Select a transport tier from payload size and locality",
            "Keep bulk payloads off the control transport",
            "Apply bounded backpressure rather than unbounded buffering",
            "Attach an integrity digest to every transfer"
        ],
        optional=[
            "Kernel-bypass transport where the node supports it",
            "Compression on the wide-area tier",
            "Opportunistic deduplication"
        ],
        non_goals=[
            "Implementing storage",
            "Authoring residency policy",
            "Carrying control-plane messages",
            "Guaranteeing delivery across a partitioned WAN"
        ],
        interfaces={
            "transfer": "PK_TRANSFER/1 - request a bulk transfer with classification and destination",
            "residency": "PK_RESIDENCY/1 - site residency labels and permitted classifications",
            "tiers": "PK_TRANSPORT_TIER/1 - available transport tiers and their size bands"
        },
        threats=[
            "Residency bypass by mislabelling a payload's classification",
            "Bulk traffic starving the control path",
            "A hostile peer claiming a residency label it does not hold",
            "Digest omission allowing silent corruption",
            "Buffer exhaustion used as a denial-of-service"
        ],
        failure_modes=[
            "Destination site is not a legal residence for the classification",
            "No transport tier covers the payload size",
            "Backpressure limit reached",
            "Digest mismatch on arrival"
        ],
        slos=[
            Slo("residency correctness", "zero transfers admitted to an illegal residence", "no budget"),
            Slo("control isolation", "zero bulk payloads observed on the control transport", "no budget"),
            Slo("bulk throughput", "p50 local-tier throughput at or above the node's measured line rate minus 10%", "5% of transfers may fall below")
        ],
        signals={
            "transfers": "counter by tier, classification, and outcome",
            "residency_refusals": "counter by classification and destination site",
            "backpressure_events": "counter of transfers delayed or refused by the limiter",
            "digest_mismatches": "counter of transfers failing integrity check",
            "bulk_bytes": "counter of bytes by transport tier"
        },
    )
