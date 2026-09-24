"""Binding contract for GAP-05 - State replication/consistency model.

The state replication and consistency model makes the edge's divergence explicit. Writes taken on both sides of a partition are kept, not silently lost: the model merges what commutes, and surfaces what genuinely conflicts for a decision instead of picking a winner by timestamp.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-05"
ELEMENT_NAME = "State replication/consistency model"


def build() -> Contract:
    """Return the production contract for GAP-05."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own replicated state semantics across sites: converge concurrent writes deterministically, detect genuine conflicts rather than resolving them by clock, and never discard a write without recording that it was discarded."
        ),
        owns=[
            "The replication consistency model and its convergence guarantee",
            "Version vectors and causal ordering",
            "Conflict detection and the conflict set",
            "Deterministic merge for commuting updates",
            "The record of every discarded write"
        ],
        not_owns=[
            "Transport between sites",
            "Storage engines",
            "Data residency policy",
            "Which sites replicate what",
            "Conflict resolution policy authorship"
        ],
        dependencies=[
            Dependency("GAP-04 Disconnected-operation controller", "upstream", "Signals when a partition begins and ends"),
            Dependency("PLN-06 Data plane", "upstream", "Carries the replication traffic"),
            Dependency("GAP-14 Data-gravity manager", "downstream", "Uses convergence state to decide where data should sit"),
            Dependency("GAP-13 Policy engine", "peer", "Supplies the resolution policy for detected conflicts")
        ],
        source_of_truth="The version vector: causality decides ordering, and wall-clock time never breaks a tie.",
        assumptions=[
            "Clocks between sites are not synchronised well enough to order writes",
            "A partition may produce concurrent writes to the same key",
            "Some value types commute and some do not"
        ],
        boundaries={
            "tenant": "replication is per tenant; no key is shared across tenants",
            "environment": "environments replicate independently",
            "site": "each site is a replica with its own version vector entry",
            "workload": "a workload writes through its site replica, never directly to another"
        },
        mandatory=[
            "Order writes by causality, never by wall-clock timestamp",
            "Converge deterministically regardless of delivery order",
            "Detect concurrent writes as conflicts rather than resolving them silently",
            "Record every discarded write",
            "Preserve both sides of a conflict until it is resolved"
        ],
        optional=[
            "CRDT types for commuting values",
            "Automatic resolution for declared-commutative keys",
            "Compaction of resolved conflict history"
        ],
        non_goals=[
            "Providing linearizability across sites",
            "Choosing a winner by timestamp",
            "Transporting replication traffic",
            "Authoring resolution policy"
        ],
        interfaces={
            "write": "PK_REPLICATED_WRITE/1 - a write with its originating site and version vector",
            "merge": "PK_MERGE_RESULT/1 - converged value or the conflict set",
            "conflicts": "PK_CONFLICT_SET/1 - unresolved concurrent writes awaiting a decision"
        },
        threats=[
            "A site forging a version vector to win every merge",
            "Clock manipulation to order a hostile write last",
            "Conflict flooding to exhaust the conflict set",
            "Silent write loss masking tampering"
        ],
        failure_modes=[
            "Concurrent writes to the same key across a partition",
            "Version vector from an unknown site",
            "Conflict set grows beyond its bound",
            "A replica replays an already-applied write"
        ],
        slos=[
            Slo("convergence", "identical write sets converge to an identical value regardless of order", "no budget"),
            Slo("write preservation", "zero writes discarded without a recorded reason", "no budget"),
            Slo("conflict detection", "100% of causally concurrent writes reported as conflicts", "no budget")
        ],
        signals={
            "replica_version": "version vector per key and site",
            "conflicts_open": "gauge of unresolved conflicts per tenant",
            "writes_discarded": "counter with the reason each write was discarded",
            "merge_operations": "counter by outcome (converged, conflict, duplicate)"
        },
    )
