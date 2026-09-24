"""Binding contract for INV-05 - Current control-state system.

The current control-state system is the consistent key-value store every controller reads and writes: each change gets a revision number, updates are compare-and-swap, and controllers watch for changes from a revision onward. The trap is compaction -- a watcher that asks for history that has been discarded must be told so, not silently given a gap.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-05"
ELEMENT_NAME = "Current control-state system"


def build() -> Contract:
    """Return the production contract for INV-05."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the control-state model: revisioned keys, compare-and-swap transactions, watches from a revision, and compaction with explicit refusal of discarded history."
        ),
        owns=[
            "Global revision numbering",
            "Compare-and-swap transactions",
            "Watch from revision",
            "Compaction",
            "Refusal of watches from compacted revisions"
        ],
        not_owns=[
            "Consensus implementation",
            "Controller logic",
            "Backups",
            "Storage hardware",
            "Authorization"
        ],
        dependencies=[
            Dependency("INV-04 Current orchestration", "upstream", "Its controllers read and write this state"),
            Dependency("GAP-05 State replication/consistency model", "downstream", "Replicates this state across sites"),
            Dependency("INV-07 GitOps transition layer", "downstream", "Compares desired state from git with this store"),
            Dependency("PLN-03 Distributed runtime plane", "peer", "The successor control state")
        ],
        source_of_truth="The store's revision; a controller's cache is valid only up to the revision it last saw.",
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
            "Give every change a new global revision",
            "Apply a transaction only if its comparisons hold",
            "Deliver every change after a watch's start revision",
            "Compact old history on schedule",
            "Refuse a watch that starts before the compaction point"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing consensus",
            "Writing controllers",
            "Taking backups"
        ],
        interfaces={
            "txn": "PK_CSTATE_TXN/1 - compare, then success or failure ops",
            "watch": "PK_CSTATE_WATCH/1 - changes from a revision",
            "compact": "PK_CSTATE_COMPACT/1 - discard history below a revision"
        },
        threats=[
            "Lost update from a blind write",
            "Controller missing events after compaction",
            "Unbounded history growth"
        ],
        failure_modes=[
            "Compare failed",
            "Revision compacted",
            "Key not found",
            "Store unavailable"
        ],
        slos=[
            Slo("linearisable writes", "zero transactions applied with a failed compare", "no budget"),
            Slo("no silent gaps", "every watch either receives all changes or is told they were compacted", "no budget"),
            Slo("write latency", "p99 under 10ms", "1% may exceed")
        ],
        signals={
            "revision": "gauge",
            "txn_conflicts": "counter",
            "compacted_refusals": "counter",
            "history_size": "gauge"
        },
    )
