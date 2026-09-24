"""Binding contract for INV-54 - Broker implementations.

Broker implementations are the concrete engines behind the messaging contract. Two ship here: a fan-out broker that copies each message to every subscriber, and a partitioned log that keeps per-key order and lets consumers replay from an offset. They make opposite trade-offs, and the contract is only portable if both pass the same checks.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-54"
ELEMENT_NAME = "Broker implementations"


def build() -> Contract:
    """Return the production contract for INV-54."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the reference brokers: fan-out and partitioned-log implementations, per-key ordering, consumer offsets and replay, and contract conformance of each."
        ),
        owns=[
            "The fan-out broker",
            "The partitioned-log broker",
            "Per-key ordering by partition",
            "Consumer offsets and replay",
            "Broker conformance against the messaging contract"
        ],
        not_owns=[
            "The messaging contract",
            "Delivery guarantees policy",
            "Cluster operation",
            "Schemas",
            "Transport"
        ],
        dependencies=[
            Dependency("INV-52 Messaging abstraction", "upstream", "Defines the contract these brokers implement"),
            Dependency("INV-53 Message reliability", "upstream", "Defines the delivery guarantees they honour"),
            Dependency("INV-49 Pluggable infrastructure adapters", "downstream", "Admits these brokers"),
            Dependency("INV-37 Bulk data plane", "peer", "Moves large payloads referenced by messages")
        ],
        source_of_truth="The partition log itself; a consumer's position is an offset into it, not a copy of it.",
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
            "Deliver every fan-out message to every subscriber",
            "Preserve order per partition key",
            "Let consumers replay from any retained offset",
            "Keep consumer offsets independent",
            "Pass the shared broker conformance checks"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Defining the contract",
            "Running a cluster",
            "Owning schemas"
        ],
        interfaces={
            "fanout": "PK_BROKER_FANOUT/1 - copy-to-all delivery",
            "log": "PK_BROKER_LOG/1 - partitioned, offset-addressed log",
            "offset": "PK_BROKER_OFFSET/1 - a consumer's committed position"
        },
        threats=[
            "Per-key reordering breaking a state machine",
            "One consumer's offset moving another's",
            "Fan-out skipping a slow subscriber"
        ],
        failure_modes=[
            "Partition unavailable",
            "Offset out of range",
            "Subscriber backlog full",
            "Conformance failure"
        ],
        slos=[
            Slo("ordering", "zero per-key reorderings in the log broker", "no budget"),
            Slo("fan-out completeness", "every subscriber receives every message", "no budget"),
            Slo("append latency", "p99 append under 2ms", "1% may exceed")
        ],
        signals={
            "appended": "counter by partition",
            "consumer_lag": "gauge by consumer",
            "replays": "counter"
        },
    )
