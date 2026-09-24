"""Binding contract for INV-53 - Message reliability.

Message reliability turns 'published' into 'processed'. Delivery is at-least-once: a message stays owned by the broker until the consumer acknowledges it, reappears if the consumer dies holding it, and after a bounded number of attempts is parked in a dead-letter queue instead of looping forever. Because redelivery happens, consumers deduplicate by message id.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-53"
ELEMENT_NAME = "Message reliability"


def build() -> Contract:
    """Return the production contract for INV-53."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own delivery guarantees: acknowledgement, visibility timeouts, redelivery, bounded attempts, dead-lettering of poison messages and consumer-side deduplication."
        ),
        owns=[
            "Acknowledgement protocol",
            "Visibility timeout and redelivery",
            "Maximum delivery attempts",
            "Poison-message dead-lettering",
            "Consumer idempotency by message id"
        ],
        not_owns=[
            "Routing rules",
            "The envelope",
            "Broker storage",
            "Business retry logic",
            "Ordering"
        ],
        dependencies=[
            Dependency("INV-52 Messaging abstraction", "upstream", "Supplies the enveloped messages"),
            Dependency("INV-54 Broker implementations", "downstream", "Implements these guarantees"),
            Dependency("INV-57 Durable execution", "downstream", "Relies on at-least-once plus idempotency"),
            Dependency("GAP-09 Unified observability", "peer", "Reports redelivery and dead-letter rates")
        ],
        source_of_truth="The broker's in-flight table; a consumer that has not acknowledged does not own the message.",
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
            "Keep every message until acknowledged",
            "Redeliver after the visibility timeout",
            "Cap delivery attempts",
            "Dead-letter a message that exhausts its attempts",
            "Deduplicate at the consumer by message id"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Routing",
            "Storing messages",
            "Ordering"
        ],
        interfaces={
            "deliver": "PK_MSG_DELIVER/1 - a leased delivery",
            "ack": "PK_MSG_ACK/1 - acknowledgement",
            "dlq": "PK_MSG_DLQ/1 - a dead-lettered message and its attempt history"
        },
        threats=[
            "Message lost when a consumer crashes",
            "Poison message looping forever",
            "Duplicate processing on redelivery"
        ],
        failure_modes=[
            "Visibility timeout expired",
            "Attempts exhausted",
            "Duplicate delivery",
            "Ack for unknown lease"
        ],
        slos=[
            Slo("no loss", "zero unacknowledged messages lost", "no budget"),
            Slo("bounded poison", "no message delivered more than its attempt cap", "no budget"),
            Slo("redelivery delay", "p99 redelivery within timeout plus 1s", "1% may exceed")
        ],
        signals={
            "in_flight": "gauge",
            "redeliveries": "counter",
            "dead_lettered": "counter",
            "duplicates_skipped": "counter"
        },
    )
