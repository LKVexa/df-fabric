"""Binding contract for INV-46 - Distributed application runtime.

A distributed application runtime gives an application its infrastructure as named building blocks -- state, pub/sub, secrets, invocation -- reached through one local API. The application never learns which database or broker sits behind a name, and a component is only reachable by the applications it is scoped to.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-46"
ELEMENT_NAME = "Distributed application runtime"


def build() -> Contract:
    """Return the production contract for INV-46."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the building-block runtime: component registration, name resolution, application scoping, and uniform invocation of building blocks regardless of the backing implementation."
        ),
        owns=[
            "Building-block registration",
            "Component-name resolution",
            "Application scoping of components",
            "Uniform invocation surface",
            "Runtime-level observability of calls"
        ],
        not_owns=[
            "Backing store and broker implementations",
            "Deployment topology",
            "Application code",
            "Authorization policy content",
            "Scheduling"
        ],
        dependencies=[
            Dependency("PLN-02 Application plane", "upstream", "Declares the applications and their components"),
            Dependency("INV-49 Pluggable infrastructure adapters", "downstream", "Implements the components this runtime resolves"),
            Dependency("INV-47 Dapr deployment model", "downstream", "Decides how this runtime is deployed beside apps"),
            Dependency("INV-59 Application authorization", "peer", "Authorizes calls this runtime routes")
        ],
        source_of_truth="The component registry with its scopes; an application's belief about what is available is not authoritative.",
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
            "Resolve every building block by component name",
            "Refuse components outside the caller's scope",
            "Keep the invocation surface identical across implementations",
            "Record every invocation",
            "Fail closed on unknown components"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing stores or brokers",
            "Deploying itself",
            "Authoring authorization policy"
        ],
        interfaces={
            "register": "PK_DAR_COMPONENT/1 - a named, typed, scoped component",
            "invoke": "PK_DAR_INVOKE/1 - a building-block call by component name",
            "scope": "PK_DAR_SCOPE/1 - which applications may reach a component"
        },
        threats=[
            "An application reaching another tenant's store by guessing its name",
            "Implementation details leaking into application code",
            "Unknown component silently defaulted"
        ],
        failure_modes=[
            "Component not found",
            "Component out of scope",
            "Building-block type mismatch",
            "Backend unavailable"
        ],
        slos=[
            Slo("scope containment", "zero calls reach a component outside the caller's scope", "no budget"),
            Slo("portability", "swapping an implementation changes zero application calls", "no budget"),
            Slo("overhead", "p99 runtime overhead under 1ms per call", "1% may exceed")
        ],
        signals={
            "invocations": "counter by block and component",
            "scope_denials": "counter",
            "resolution_failures": "counter",
            "call_latency": "histogram"
        },
    )
