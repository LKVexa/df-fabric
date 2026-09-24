"""Binding contract for INV-52 - Messaging abstraction.

The messaging abstraction lets an application publish to a topic and subscribe to one without knowing the broker. Every message travels in one envelope -- id, source, type, time, data -- and subscriptions route by rule, with a dead-letter topic for what no rule or handler can take.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-52"
ELEMENT_NAME = "Messaging abstraction"


def build() -> Contract:
    """Return the production contract for INV-52."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the publish/subscribe contract: the message envelope, topic and subscription model, content-based routing rules and dead-letter routing."
        ),
        owns=[
            "The message envelope",
            "Topic and subscription model",
            "Content-based routing rules",
            "Dead-letter routing",
            "Topic-level access scoping"
        ],
        not_owns=[
            "Broker implementations",
            "Delivery guarantees and redelivery",
            "Message schemas",
            "Transport",
            "Consumer business logic"
        ],
        dependencies=[
            Dependency("INV-46 Distributed application runtime", "upstream", "Routes pub/sub calls to this contract"),
            Dependency("INV-49 Pluggable infrastructure adapters", "upstream", "Admits brokers against this contract"),
            Dependency("INV-53 Message reliability", "downstream", "Adds delivery guarantees to this contract"),
            Dependency("INV-54 Broker implementations", "downstream", "Implements this contract")
        ],
        source_of_truth="The envelope as published; a subscriber's view of a message is a projection of it.",
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
            "Wrap every message in a complete envelope",
            "Route by explicit subscription rules",
            "Send unroutable messages to a dead-letter topic",
            "Scope publishing per topic",
            "Keep the contract broker-independent"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing brokers",
            "Guaranteeing delivery",
            "Defining payload schemas"
        ],
        interfaces={
            "publish": "PK_MSG_PUBLISH/1 - an enveloped message to a topic",
            "subscribe": "PK_MSG_SUBSCRIBE/1 - a routed subscription",
            "envelope": "PK_MSG_ENVELOPE/1 - id, source, type, time, data"
        },
        threats=[
            "Publishing to a topic the app does not own",
            "Message silently dropped when no route matches",
            "Envelope missing its source, defeating tracing"
        ],
        failure_modes=[
            "Topic not permitted",
            "No route matched",
            "Envelope incomplete",
            "Broker unavailable"
        ],
        slos=[
            Slo("no silent drops", "every unroutable message reaches the dead-letter topic", "no budget"),
            Slo("envelope completeness", "zero messages published without id and source", "no budget"),
            Slo("publish latency", "p99 publish overhead under 1ms", "1% may exceed")
        ],
        signals={
            "published": "counter by topic",
            "dead_lettered": "counter by reason",
            "routed": "counter by rule"
        },
    )
