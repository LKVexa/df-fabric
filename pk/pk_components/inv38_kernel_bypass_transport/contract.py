"""Binding contract for INV-38 - Kernel-bypass transport.

Kernel-bypass transport hands network or storage queues straight to user space, skipping the kernel copy. The speed comes from the application touching device-visible memory directly, which is exactly the danger: every access must fall inside a registered region, and the sealed end-to-end channel above it must not be weakened just because the path got faster.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-38"
ELEMENT_NAME = "Kernel-bypass transport"


def build() -> Contract:
    """Return the production contract for INV-38."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the bypass fast path: memory region registration, bounds-checked descriptor posting, completion rings, and transparent fallback to the kernel path when bypass is unavailable."
        ),
        owns=[
            "Memory region registration and keys",
            "Bounds checks on every posted descriptor",
            "Submission and completion rings",
            "Fallback to the kernel path",
            "Keeping end-to-end sealing above the bypass layer"
        ],
        not_owns=[
            "Control semantics",
            "Chunk verification",
            "Device drivers",
            "Placement",
            "Key custody"
        ],
        dependencies=[
            Dependency("INV-35 High-performance VM I/O", "upstream", "Provides the device queues being bypassed into"),
            Dependency("INV-36 Control transport", "upstream", "Its sealed frames ride this path unchanged"),
            Dependency("GAP-12 WAN resilience and NAT traversal", "downstream", "Uses bypass where the link supports it"),
            Dependency("INV-37 Bulk data plane", "peer", "Moves verified chunks over the fast path")
        ],
        source_of_truth="The registration table; an address outside a registered region does not exist to the device.",
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
            "Register memory before the device may touch it",
            "Bounds-check every descriptor",
            "Deliver completions in order through the ring",
            "Fall back to the kernel path transparently",
            "Carry sealed frames without unsealing them"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Writing device drivers",
            "Verifying payloads",
            "Weakening encryption for speed"
        ],
        interfaces={
            "register": "PK_BYPASS_MR/1 - a registered memory region and its key",
            "post": "PK_BYPASS_POST/1 - a descriptor posted against a region",
            "complete": "PK_BYPASS_CQ/1 - a completion entry"
        },
        threats=[
            "Descriptor pointing outside a registered region",
            "Stale region key reused after deregistration",
            "Plaintext exposed because the fast path skipped sealing",
            "Ring overflow losing completions"
        ],
        failure_modes=[
            "Region not registered",
            "Descriptor out of bounds",
            "Ring full",
            "Bypass unavailable"
        ],
        slos=[
            Slo("memory safety", "zero device accesses outside registered regions", "no budget"),
            Slo("sealing preserved", "the fast path carries only sealed frames", "no budget"),
            Slo("latency", "p99 post-to-completion under 5us", "1% may exceed")
        ],
        signals={
            "regions": "gauge",
            "bounds_violations": "counter",
            "fallbacks": "counter by reason",
            "ring_depth": "gauge"
        },
    )
