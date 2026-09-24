"""Binding contract for INV-71 - Heavy agent sandbox.

The heavy agent sandbox is for code the fast sandbox cannot or should not hold: real interpreters, package installs, browsers. Each agent session gets its own microVM-class boundary with a filesystem that starts from a clean snapshot, egress limited to an allowlist, and a teardown that leaves nothing behind for the next session to find.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-71"
ELEMENT_NAME = "Heavy agent sandbox"


def build() -> Contract:
    """Return the production contract for INV-71."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the heavyweight session sandbox: per-session isolation, clean-snapshot filesystems, egress allowlists, resource limits and verified teardown."
        ),
        owns=[
            "Per-session isolation boundary",
            "Clean-snapshot filesystem per session",
            "Egress allowlisting",
            "Session resource limits",
            "Verified teardown"
        ],
        not_owns=[
            "Hypervisor implementation",
            "Tool business logic",
            "Model execution",
            "Credential issuance",
            "Long-term storage"
        ],
        dependencies=[
            Dependency("INV-69 Agentic workload layer", "upstream", "Routes high-risk tool execution here"),
            Dependency("INV-24 MicroVM runtime", "upstream", "Provides the per-session isolation boundary"),
            Dependency("INV-26 MicroVM snapshotting", "upstream", "Provides the clean base snapshot"),
            Dependency("GAP-09 Unified observability", "downstream", "Receives egress and teardown records")
        ],
        source_of_truth="The clean base snapshot; every session is that snapshot plus only its own writes.",
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
            "Isolate every session in its own boundary",
            "Start every session from the clean snapshot",
            "Refuse egress outside the allowlist",
            "Enforce session resource limits",
            "Verify nothing survives teardown"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Implementing hypervisors",
            "Running models",
            "Issuing credentials"
        ],
        interfaces={
            "session": "PK_HEAVYBOX_SESSION/1 - an isolated agent session",
            "egress": "PK_HEAVYBOX_EGRESS/1 - an allow or deny decision",
            "teardown": "PK_HEAVYBOX_TEARDOWN/1 - a verified teardown record"
        },
        threats=[
            "Data from one session visible to the next",
            "Exfiltration to an arbitrary host",
            "Session consuming the host"
        ],
        failure_modes=[
            "Egress denied",
            "Resource limit hit",
            "Snapshot unavailable",
            "Teardown incomplete"
        ],
        slos=[
            Slo("session isolation", "zero bytes carried from one session to another", "no budget"),
            Slo("egress containment", "zero connections outside the allowlist", "no budget"),
            Slo("session start", "p99 under 250ms from snapshot", "1% may exceed")
        ],
        signals={
            "sessions": "gauge",
            "egress_denied": "counter by host",
            "teardowns_verified": "counter"
        },
    )
