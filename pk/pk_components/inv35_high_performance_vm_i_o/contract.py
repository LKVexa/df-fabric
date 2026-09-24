"""Binding contract for INV-35 - High-performance VM I/O.

High-performance VM I/O is virtio done properly: shared-memory rings, notification suppression and a vhost-style datapath that keeps the VMM out of the hot path. Every one of those tricks is also a way for a guest to corrupt the host, so descriptor validation here is not optional.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-35"
ELEMENT_NAME = "High-performance VM I/O"


def build() -> Contract:
    """Return the production contract for INV-35."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the guest-host I/O datapath: validate every descriptor a guest places on a ring against the guest's own memory bounds, bound in-flight work per queue, and refuse a descriptor that would read or write outside the guest's memory."
        ),
        owns=[
            "Virtqueue descriptor validation",
            "Guest memory bounds checking on the datapath",
            "In-flight depth per queue",
            "Notification suppression and its correctness",
            "Refusal of malformed or out-of-bounds descriptors"
        ],
        not_owns=[
            "Device semantics",
            "Guest drivers",
            "The network or storage backend",
            "Device model membership",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-25 MicroVM devices", "upstream", "Defines which devices have a datapath at all"),
            Dependency("INV-24 MicroVM runtime", "upstream", "Owns the guest whose memory bounds are checked"),
            Dependency("PLN-06 Data plane", "downstream", "Bulk transfers ride this datapath"),
            Dependency("INV-43 Transient-execution defense", "peer", "Mitigations change the cost of ring transitions", required=False)
        ],
        source_of_truth="The guest's registered memory regions; a descriptor pointing outside them is invalid regardless of what the ring says.",
        assumptions=[
            "A guest can write arbitrary values into its own descriptor ring",
            "Descriptor chains may loop or be malformed",
            "Notification suppression is a correctness hazard as well as a performance win"
        ],
        boundaries={
            "tenant": "a queue belongs to one guest and one tenant",
            "environment": "queue depths differ per environment",
            "site": "sites differ in whether a vhost datapath is available",
            "workload": "each device instance has its own queues"
        },
        mandatory=[
            "Validate every descriptor against the guest's registered memory regions",
            "Refuse descriptor chains that loop or exceed the maximum length",
            "Bound in-flight descriptors per queue",
            "Never dereference a guest-supplied address without bounds checking",
            "Keep notification suppression from losing a wakeup"
        ],
        optional=[
            "vhost offload to a dedicated thread",
            "Indirect descriptors",
            "Batched completions"
        ],
        non_goals=[
            "Implementing device semantics",
            "Writing guest drivers",
            "Trusting a descriptor because the ring index moved",
            "Backend storage or networking"
        ],
        interfaces={
            "submit": "PK_VIRTQUEUE_SUBMIT/1 - a guest-posted descriptor chain",
            "complete": "PK_VIRTQUEUE_COMPLETE/1 - completion and notification decision"
        },
        threats=[
            "A descriptor pointing at host memory",
            "A descriptor chain loop hanging the datapath",
            "Queue flooding exhausting host resources",
            "A lost wakeup stalling the guest indefinitely"
        ],
        failure_modes=[
            "Descriptor outside guest memory",
            "Chain loops or is too long",
            "Queue at its in-flight bound",
            "Notification suppressed with work still pending"
        ],
        slos=[
            Slo("memory safety", "zero descriptors dereferenced outside guest memory", "no budget"),
            Slo("liveness", "zero lost wakeups with work pending", "no budget"),
            Slo("throughput", "p50 at or above 90% of the backend's line rate", "5% may fall below")
        ],
        signals={
            "descriptors_validated": "counter by outcome",
            "bounds_violations": "counter of refused out-of-bounds descriptors",
            "chain_violations": "counter of looping or over-long chains",
            "queue_depth": "gauge of in-flight descriptors per queue",
            "suppressed_notifications": "counter of notifications correctly elided"
        },
    )
