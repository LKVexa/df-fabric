"""Binding contract for INV-60 - Wasm application fabric.

A Wasm application fabric runs components across a lattice of hosts and wires them to capability providers by link name at run time. A component says 'I need a key-value store'; the fabric links it to one, routes calls across hosts, and restarts it elsewhere if a host goes. Artifacts are content-addressed, so what runs is exactly what was signed.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-60"
ELEMENT_NAME = "Wasm application fabric"


def build() -> Contract:
    """Return the production contract for INV-60."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the lattice runtime: host membership, component instantiation from content-addressed artifacts, run-time linking to providers, cross-host call routing and failover."
        ),
        owns=[
            "Lattice host membership",
            "Content-addressed component instantiation",
            "Run-time links to providers",
            "Cross-host call routing",
            "Failover of components off lost hosts"
        ],
        not_owns=[
            "Declarative deployment specs",
            "Provider implementations",
            "Artifact signing",
            "The component model",
            "Edge topology decisions"
        ],
        dependencies=[
            Dependency("INV-10 Component composition system", "upstream", "Defines the components the fabric runs"),
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Signs the artifacts the fabric pulls"),
            Dependency("INV-63 Wasm deployment manager", "downstream", "Declares what the fabric should run"),
            Dependency("INV-65 Capability providers", "peer", "The providers components are linked to")
        ],
        source_of_truth="The artifact digest; a component is the bytes that hash to its reference, whatever its tag says.",
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
            "Instantiate only artifacts whose digest matches",
            "Link components to providers by link name",
            "Route calls to a live instance on any host",
            "Reschedule components off lost hosts",
            "Refuse calls over unlinked capabilities"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Declaring deployments",
            "Implementing providers",
            "Signing artifacts"
        ],
        interfaces={
            "instantiate": "PK_LATTICE_START/1 - a component from a digest reference",
            "link": "PK_LATTICE_LINK/1 - component, link name, provider",
            "call": "PK_LATTICE_CALL/1 - a routed cross-host invocation"
        },
        threats=[
            "Tag substitution running an unsigned artifact",
            "Call over a capability never linked",
            "Component lost with its host"
        ],
        failure_modes=[
            "Digest mismatch",
            "No link for capability",
            "No live instance",
            "Host lost"
        ],
        slos=[
            Slo("artifact integrity", "zero components started from mismatched bytes", "no budget"),
            Slo("failover", "components on a lost host restarted within 10s", "1% may exceed"),
            Slo("routing overhead", "p99 cross-host call overhead under 3ms", "1% may exceed")
        ],
        signals={
            "instances": "gauge by host",
            "links": "gauge",
            "failovers": "counter",
            "digest_refusals": "counter"
        },
    )
