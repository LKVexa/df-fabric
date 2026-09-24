"""Binding contract for INV-65 - Capability providers.

Capability providers are the long-lived processes that give components access to the outside world -- a key-value store, an HTTP server, a message broker -- behind a contract id. One provider serves many links, so the rule that matters is isolation between them: each link has its own configuration and credentials, and one component cannot see or use another's.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-65"
ELEMENT_NAME = "Capability providers"


def build() -> Contract:
    """Return the production contract for INV-65."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own provider lifecycle and link isolation: contract identity, per-link configuration, health checking, and restart without losing link state."
        ),
        owns=[
            "Provider contract identity",
            "Per-link configuration and credentials",
            "Link isolation",
            "Provider health checks",
            "Restart with link-state restoration"
        ],
        not_owns=[
            "Component logic",
            "The backing services",
            "Link authorization policy",
            "Artifact signing",
            "Scheduling providers"
        ],
        dependencies=[
            Dependency("INV-60 Wasm application fabric", "upstream", "Links components to providers"),
            Dependency("INV-55 Secrets integration", "upstream", "Supplies per-link credentials"),
            Dependency("INV-64 Application model", "downstream", "Declares provider links"),
            Dependency("INV-61 Distributed WIT RPC", "peer", "Carries component-to-provider calls")
        ],
        source_of_truth="The provider's link table; configuration belongs to a link, never to the provider as a whole.",
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
            "Identify every provider by contract id",
            "Keep configuration per link",
            "Refuse a call whose link is not established",
            "Report health honestly",
            "Restore every link after restart"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing backends",
            "Authorizing links",
            "Scheduling"
        ],
        interfaces={
            "link": "PK_PROVIDER_LINK/1 - component, link name, config",
            "health": "PK_PROVIDER_HEALTH/1 - provider health status",
            "contract": "PK_PROVIDER_CONTRACT/1 - contract id the provider implements"
        },
        threats=[
            "One link's credentials used for another component",
            "Links lost on provider restart",
            "Unhealthy provider reporting healthy"
        ],
        failure_modes=[
            "Link not found",
            "Backend unhealthy",
            "Config invalid",
            "Restart failed"
        ],
        slos=[
            Slo("isolation", "zero calls served with another link's configuration", "no budget"),
            Slo("restart continuity", "every link restored after restart", "no budget"),
            Slo("call overhead", "p99 provider dispatch under 1ms", "1% may exceed")
        ],
        signals={
            "links": "gauge",
            "calls": "counter by link",
            "restarts": "counter",
            "health": "gauge"
        },
    )
