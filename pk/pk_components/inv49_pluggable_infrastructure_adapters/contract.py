"""Binding contract for INV-49 - Pluggable infrastructure adapters.

Pluggable infrastructure adapters are how a new database or broker joins the runtime without changing an application. The value is only real if the plug is checked: an adapter declares the contract and optional features it implements, and the loader verifies that declaration against the adapter itself before admitting it -- a claimed feature that is not there is refused at load, not discovered in production.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-49"
ELEMENT_NAME = "Pluggable infrastructure adapters"


def build() -> Contract:
    """Return the production contract for INV-49."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own adapter admission: contract declaration, method-level conformance checking, feature verification, version pinning and isolation of adapter failures from the runtime."
        ),
        owns=[
            "Adapter contract declarations",
            "Load-time conformance verification",
            "Optional-feature verification",
            "Adapter version pinning",
            "Containment of adapter faults"
        ],
        not_owns=[
            "The backing systems themselves",
            "Building-block semantics",
            "Application code",
            "Credentials",
            "Deployment"
        ],
        dependencies=[
            Dependency("INV-46 Distributed application runtime", "upstream", "Resolves the components adapters implement"),
            Dependency("INV-50 State abstraction", "downstream", "Defines the state contract adapters must meet"),
            Dependency("INV-52 Messaging abstraction", "downstream", "Defines the messaging contract adapters must meet"),
            Dependency("GAP-15 Runtime compatibility certification", "peer", "Certifies adapters admitted here")
        ],
        source_of_truth="The verified capability set recorded at admission; an adapter's self-description is a claim until verified.",
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
            "Declare the contract and version each adapter implements",
            "Verify every required method at load",
            "Verify every declared optional feature at load",
            "Pin adapter versions",
            "Contain an adapter fault to the component using it"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing backends",
            "Defining contracts",
            "Holding credentials"
        ],
        interfaces={
            "declare": "PK_ADAPTER_DECL/1 - contract, version and features claimed",
            "admit": "PK_ADAPTER_ADMIT/1 - the verified admission record",
            "contract": "PK_ADAPTER_CONTRACT/1 - required and optional methods"
        },
        threats=[
            "Adapter claiming transactions it does not implement",
            "Unpinned adapter changing behaviour on upgrade",
            "Adapter exception crashing the runtime"
        ],
        failure_modes=[
            "Required method missing",
            "Declared feature missing",
            "Version not pinned",
            "Adapter raised"
        ],
        slos=[
            Slo("honest admission", "zero adapters admitted with an unverified feature claim", "no budget"),
            Slo("containment", "an adapter fault affects only its own component", "no budget"),
            Slo("load time", "p99 admission check under 50ms", "1% may exceed")
        ],
        signals={
            "admitted": "gauge by contract",
            "refused": "counter by reason",
            "adapter_faults": "counter"
        },
    )
