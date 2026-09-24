"""Binding contract for INV-36 - Control transport.

The control transport carries the small, authoritative messages -- placement decisions, leases, revocations -- that everything else acts on. Its job is not speed but trust: every frame is authenticated, sequenced and sealed end to end, so a relay in the middle forwards ciphertext it cannot read or reorder undetected.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-36"
ELEMENT_NAME = "Control transport"


def build() -> Contract:
    """Return the production contract for INV-36."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the control-message channel: session keying, per-frame authentication and sealing, sequence ordering, replay rejection and frame bounding, end to end across any relay."
        ),
        owns=[
            "Session establishment and key derivation",
            "Per-frame sealing and authentication",
            "Monotonic sequencing and replay rejection",
            "Frame size bounds",
            "End-to-end confidentiality across relays"
        ],
        not_owns=[
            "Bulk payload movement",
            "NAT traversal and relay selection",
            "Key custody",
            "Message semantics",
            "Scheduling"
        ],
        dependencies=[
            Dependency("GAP-06 Device identity/attestation", "upstream", "Supplies the identities a session is bound to"),
            Dependency("GAP-12 WAN resilience and NAT traversal", "downstream", "Relays sealed control frames it cannot open"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Sends leases and placements over this channel"),
            Dependency("INV-37 Bulk data plane", "peer", "Carries the large payloads this channel only references")
        ],
        source_of_truth="The sealed frame as the receiver verifies it; nothing a relay reports about a frame is trusted.",
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
            "Seal every frame end to end",
            "Authenticate every frame before acting on it",
            "Reject replayed or reordered frames",
            "Bound frame size",
            "Never expose plaintext to a relay"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Moving bulk data",
            "Choosing relays",
            "Holding long-term keys",
            "Interpreting control messages"
        ],
        interfaces={
            "session": "PK_CTRL_SESSION/1 - a keyed, sequenced control session",
            "frame": "PK_CTRL_FRAME/1 - one sealed, authenticated control frame",
            "relay": "PK_CTRL_RELAY/1 - opaque forwarding of sealed frames"
        },
        threats=[
            "Relay operator reading control traffic",
            "Replay of a stale revocation or lease",
            "Frame tampering in transit",
            "Oversized frame exhausting receiver memory"
        ],
        failure_modes=[
            "Authentication failure",
            "Replay detected",
            "Frame too large",
            "Session key mismatch"
        ],
        slos=[
            Slo("authenticity", "zero unauthenticated frames acted upon", "no budget"),
            Slo("relay blindness", "zero plaintext bytes visible to any relay", "no budget"),
            Slo("control latency", "p99 seal+open under 50us per frame", "1% may exceed")
        ],
        signals={
            "frames_sealed": "counter by session",
            "auth_failures": "counter by reason",
            "replays_rejected": "counter by session",
            "frame_bytes": "histogram"
        },
    )
