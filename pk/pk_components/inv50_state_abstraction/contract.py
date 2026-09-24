"""Binding contract for INV-50 - State abstraction.

The state abstraction is a key/value contract with the concurrency rules written down: every value carries an etag, a write that names a stale etag is refused, and keys are namespaced by application so two apps sharing a store cannot read each other's data by picking the same key.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-50"
ELEMENT_NAME = "State abstraction"


def build() -> Contract:
    """Return the production contract for INV-50."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the state contract: namespaced keys, etag-based optimistic concurrency, first-write and last-write modes, bulk operations and the consistency guarantees each mode gives."
        ),
        owns=[
            "Key namespacing per application",
            "Etag optimistic concurrency",
            "Concurrency mode selection",
            "Bulk get and set semantics",
            "The contract every state store must meet"
        ],
        not_owns=[
            "Store implementations",
            "Replication between sites",
            "Encryption at rest",
            "Query languages",
            "Backups"
        ],
        dependencies=[
            Dependency("INV-46 Distributed application runtime", "upstream", "Routes state calls to this contract"),
            Dependency("INV-49 Pluggable infrastructure adapters", "upstream", "Admits stores against this contract"),
            Dependency("INV-51 Example state stores", "downstream", "Implements this contract"),
            Dependency("GAP-05 State replication/consistency model", "peer", "Replicates what this contract stores")
        ],
        source_of_truth="The etag the store holds for a key; a caller's cached value is stale the moment the etag moves.",
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
            "Namespace every key by application",
            "Return an etag with every read",
            "Refuse a first-write-wins write with a stale etag",
            "Make bulk writes all-or-nothing",
            "Document the consistency each mode gives"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing stores",
            "Replicating across sites",
            "Encrypting at rest"
        ],
        interfaces={
            "get": "PK_STATE_GET/1 - value and etag",
            "set": "PK_STATE_SET/1 - write with optional etag",
            "bulk": "PK_STATE_BULK/1 - atomic multi-key write"
        },
        threats=[
            "Lost update from concurrent writers",
            "Cross-application key collision",
            "Partial bulk write leaving inconsistent state"
        ],
        failure_modes=[
            "Etag mismatch",
            "Key not found",
            "Bulk write aborted",
            "Store unavailable"
        ],
        slos=[
            Slo("no lost updates", "zero stale-etag writes accepted in first-write mode", "no budget"),
            Slo("isolation", "zero reads across application namespaces", "no budget"),
            Slo("latency", "p99 single-key operation overhead under 1ms", "1% may exceed")
        ],
        signals={
            "ops": "counter by op",
            "etag_conflicts": "counter",
            "bulk_aborts": "counter"
        },
    )
