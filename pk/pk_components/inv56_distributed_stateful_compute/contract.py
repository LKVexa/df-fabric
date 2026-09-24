"""Binding contract for INV-56 - Distributed stateful compute.

Distributed stateful compute is the virtual-actor model: an actor is addressed by id, activated on some host when first called, and processes one message at a time. The guarantees that make it useful are single activation -- never two live copies of the same actor -- and turn-based execution, so actor code needs no locks.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-56"
ELEMENT_NAME = "Distributed stateful compute"


def build() -> Contract:
    """Return the production contract for INV-56."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own virtual actors: placement and single activation, turn-based message processing, idle deactivation with state persistence, and reactivation elsewhere after host loss."
        ),
        owns=[
            "Actor placement table",
            "Single-activation guarantee",
            "Turn-based concurrency",
            "Idle deactivation and state persistence",
            "Reactivation after host failure"
        ],
        not_owns=[
            "State store implementation",
            "Actor business logic",
            "Host provisioning",
            "Network transport",
            "Scheduling of hosts"
        ],
        dependencies=[
            Dependency("INV-50 State abstraction", "upstream", "Persists actor state between activations"),
            Dependency("PLN-03 Distributed runtime plane", "upstream", "Supplies the hosts actors are placed on"),
            Dependency("INV-57 Durable execution", "downstream", "Builds long-running workflows beside actors"),
            Dependency("INV-48 Service communication APIs", "peer", "Carries calls to remote actors")
        ],
        source_of_truth="The placement table; an actor lives where the table says and nowhere else.",
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
            "Activate each actor on exactly one host",
            "Process one message at a time per actor",
            "Persist state on deactivation",
            "Reactivate lost actors elsewhere with their state",
            "Route every call through placement"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing storage",
            "Writing actor logic",
            "Provisioning hosts"
        ],
        interfaces={
            "call": "PK_ACTOR_CALL/1 - a message to an actor id",
            "placement": "PK_ACTOR_PLACEMENT/1 - actor id to host",
            "state": "PK_ACTOR_STATE/1 - persisted actor state"
        },
        threats=[
            "Split brain with two live activations",
            "Concurrent turns corrupting state",
            "State lost on deactivation"
        ],
        failure_modes=[
            "Host lost",
            "Placement conflict",
            "State persistence failed",
            "Turn timeout"
        ],
        slos=[
            Slo("single activation", "zero actors with two live activations", "no budget"),
            Slo("turn isolation", "zero overlapping turns per actor", "no budget"),
            Slo("activation latency", "p99 cold activation under 50ms", "1% may exceed")
        ],
        signals={
            "activations": "counter",
            "deactivations": "counter",
            "reactivations": "counter by cause",
            "turn_ms": "histogram"
        },
    )
