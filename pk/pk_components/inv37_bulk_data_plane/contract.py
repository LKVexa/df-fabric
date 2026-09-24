"""Binding contract for INV-37 - Bulk data plane.

The bulk data plane moves the large things -- images, snapshots, model weights, datasets -- in verified chunks. Every chunk carries its own digest and the object carries a digest over the chunk list, so a transfer is checked end to end by the receiver, can resume from the last good chunk, and never trusts the transport to have delivered what it claims.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-37"
ELEMENT_NAME = "Bulk data plane"


def build() -> Contract:
    """Return the production contract for INV-37."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own chunked bulk transfer: chunking, per-chunk and whole-object digests, receiver-side end-to-end verification, resumption and bounded concurrency."
        ),
        owns=[
            "Content chunking and manifests",
            "Per-chunk digest verification",
            "Whole-object end-to-end verification",
            "Resumable transfer state",
            "Transfer concurrency bounds"
        ],
        not_owns=[
            "Control messages",
            "Placement of data",
            "Storage backends",
            "Encryption key custody",
            "Deciding what to move"
        ],
        dependencies=[
            Dependency("INV-36 Control transport", "upstream", "Carries the manifest references this plane fetches against"),
            Dependency("GAP-14 Data gravity manager", "upstream", "Decides which objects move and where"),
            Dependency("PLN-06 Data plane", "downstream", "Relies on this plane's end-to-end digest verification"),
            Dependency("INV-38 Kernel-bypass transport", "peer", "An alternative fast path for the same chunks")
        ],
        source_of_truth="The manifest digest the receiver recomputes; a transport's success report is never evidence of integrity.",
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
            "Chunk every object with a manifest",
            "Verify every chunk digest on receipt",
            "Verify the whole-object digest end to end",
            "Resume from the last verified chunk",
            "Bound concurrent transfers"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Carrying control messages",
            "Choosing placement",
            "Implementing storage"
        ],
        interfaces={
            "manifest": "PK_BULK_MANIFEST/1 - chunk list and object digest",
            "chunk": "PK_BULK_CHUNK/1 - one digested chunk",
            "resume": "PK_BULK_RESUME/1 - the last verified chunk index"
        },
        threats=[
            "Corrupted chunk accepted as valid",
            "Manifest substitution",
            "Partial object used as complete",
            "Unbounded parallel transfers exhausting bandwidth"
        ],
        failure_modes=[
            "Chunk digest mismatch",
            "Manifest digest mismatch",
            "Transfer interrupted",
            "Concurrency limit reached"
        ],
        slos=[
            Slo("integrity", "zero objects accepted without end-to-end digest verification", "no budget"),
            Slo("resumption", "an interrupted transfer re-sends only unverified chunks", "no budget"),
            Slo("throughput", "p50 throughput within 10% of link capacity", "5% of transfers may fall below")
        ],
        signals={
            "chunks_verified": "counter",
            "digest_failures": "counter by level",
            "bytes_resent": "counter",
            "transfers_active": "gauge"
        },
    )
