"""Binding contract for INV-21 - Local service chaining.

Local service chaining is what makes the component model pay off operationally: when component A calls component B and both are on the same host, the call never becomes a network request. It becomes a direct invocation, with the same interface, the same capability checks and the same observability -- the topology changes, the semantics do not.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-21"
ELEMENT_NAME = "Local service chaining"


def build() -> Contract:
    """Return the production contract for INV-21."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the local call path between co-resident components: resolution, the decision to chain locally or fall back to the network, loop prevention, depth bounding and preservation of identity and trace context across the hop."
        ),
        owns=[
            "Co-residency detection and local dispatch",
            "Chain depth and cycle bounding",
            "Identity and trace propagation across a local hop",
            "Fallback to the network path when the callee is remote",
            "Per-hop capability re-checking"
        ],
        not_owns=[
            "Placement decisions",
            "The network transport",
            "Interface definitions",
            "Service discovery beyond the local host",
            "Business logic"
        ],
        dependencies=[
            Dependency("INV-20 HTTP component worlds", "upstream", "Supplies the handler being chained to"),
            Dependency("INV-10 Component composition system", "upstream", "Knows which components are linked"),
            Dependency("INV-16 Async component functions", "upstream", "The chained call is an async function call"),
            Dependency("INV-13 System interface", "peer", "Capability checks are re-run on each hop"),
            Dependency("SCH-01 Multi-runtime scheduler", "downstream", "Local chaining changes the scheduler's work shape")
        ],
        source_of_truth="The local residency table; if the callee is not in it the call goes to the network, and a stale entry is a correctness bug, not an optimisation miss.",
        assumptions=[
            "Many chains are between components that happen to share a host",
            "A local call must be indistinguishable from a remote one to the caller",
            "Cycles between components are possible and must terminate"
        ],
        boundaries={
            "tenant": "local chaining never crosses a tenant boundary",
            "environment": "residency differs per environment",
            "site": "a callee is local only on the same host",
            "workload": "chain depth limits are per workload"
        },
        mandatory=[
            "Dispatch locally when the callee is co-resident and same-tenant",
            "Fall back to the network transparently when it is not",
            "Bound chain depth",
            "Detect and refuse cycles",
            "Re-check capabilities on every hop and propagate trace context"
        ],
        optional=[
            "Argument handoff without serialisation",
            "Chain-aware batching",
            "Speculative local dispatch"
        ],
        non_goals=[
            "Deciding placement",
            "Implementing the network transport",
            "Changing call semantics for local hops",
            "Allowing cross-tenant local calls"
        ],
        interfaces={
            "chain": "PK_LOCAL_CHAIN/1 - a call routed locally or remotely",
            "residency": "PK_RESIDENCY/1 - which components share this host",
            "depth": "PK_CHAIN_DEPTH/1 - the current chain depth and its bound"
        },
        threats=[
            "A cross-tenant local call bypassing network policy",
            "Unbounded chain depth exhausting the stack",
            "A cycle spinning forever",
            "Trace context lost on the local path, hiding the hop"
        ],
        failure_modes=[
            "Chain depth exceeded",
            "Cycle detected",
            "Callee not resident and network unavailable",
            "Capability refused on a hop"
        ],
        slos=[
            Slo("semantic identity", "local and remote calls produce identical results", "no budget"),
            Slo("tenant containment", "zero local calls across a tenant boundary", "no budget"),
            Slo("local hop cost", "p99 local dispatch under 20us versus milliseconds over the network", "1% may exceed")
        ],
        signals={
            "hops_local": "counter by caller/callee pair",
            "hops_remote": "counter by reason for remoting",
            "cycles_refused": "counter by chain",
            "depth_exceeded": "counter by workload"
        },
    )
