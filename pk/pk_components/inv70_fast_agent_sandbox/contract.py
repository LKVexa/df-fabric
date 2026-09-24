"""Binding contract for INV-70 - Fast agent sandbox.

The fast agent sandbox runs small pieces of untrusted logic in microseconds: a tiny stack machine with a fuel counter, a hard memory ceiling, and no host access except through capabilities the agent was granted. It is fast because it is small, and safe because a program that runs out of fuel, memory or permissions simply stops with a reason.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-70"
ELEMENT_NAME = "Fast agent sandbox"


def build() -> Contract:
    """Return the production contract for INV-70."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the lightweight sandbox: a bounded interpreter, fuel metering, memory ceilings, capability-gated host calls and deterministic termination."
        ),
        owns=[
            "The bounded stack interpreter",
            "Fuel metering",
            "Memory ceiling",
            "Capability-gated host calls",
            "Deterministic termination with a reason"
        ],
        not_owns=[
            "High-risk arbitrary code",
            "Model execution",
            "Tool business logic",
            "Network access by default",
            "Persistent storage"
        ],
        dependencies=[
            Dependency("INV-69 Agentic workload layer", "upstream", "Routes low-risk tool logic here"),
            Dependency("INV-09 Portable compute ISA", "upstream", "The deterministic profile this interpreter follows"),
            Dependency("INV-71 Heavy agent sandbox", "peer", "Takes what this sandbox is too small for"),
            Dependency("GAP-09 Unified observability", "downstream", "Reports fuel and termination reasons")
        ],
        source_of_truth="The fuel and memory counters; a program's own claim to be finished is irrelevant.",
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
            "Meter every instruction against fuel",
            "Enforce the memory ceiling",
            "Refuse host calls without a capability",
            "Terminate deterministically with a reason",
            "Start every run from a clean state"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running arbitrary native code",
            "Granting network by default",
            "Persisting state"
        ],
        interfaces={
            "run": "PK_FASTBOX_RUN/1 - program, fuel, memory, capabilities",
            "result": "PK_FASTBOX_RESULT/1 - value or termination reason",
            "hostcall": "PK_FASTBOX_HOSTCALL/1 - a capability-gated call"
        },
        threats=[
            "Infinite loop pinning a core",
            "Memory bomb",
            "Escape to host through an ungranted call"
        ],
        failure_modes=[
            "Out of fuel",
            "Out of memory",
            "Capability denied",
            "Invalid instruction"
        ],
        slos=[
            Slo("termination", "every run terminates within its fuel", "no budget"),
            Slo("containment", "zero host calls without capability", "no budget"),
            Slo("startup", "p99 run start under 50us", "1% may exceed")
        ],
        signals={
            "runs": "counter",
            "terminations": "counter by reason",
            "fuel_used": "histogram"
        },
    )
