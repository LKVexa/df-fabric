"""Binding contract for INV-61 - Distributed WIT RPC.

Distributed WIT RPC carries typed interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-61"
ELEMENT_NAME = "Distributed WIT RPC"


def build() -> Contract:
    """Return the production contract for INV-61."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own cross-host typed invocation: frame format, signature fingerprints, receiver-side compatibility checks, typed error returns and deadlines."
        ),
        owns=[
            "RPC frame format",
            "Signature fingerprinting",
            "Receiver-side compatibility check",
            "Typed error returns",
            "Per-call deadlines"
        ],
        not_owns=[
            "Interface definitions",
            "Transport encryption",
            "Service discovery",
            "Component logic",
            "Load balancing"
        ],
        dependencies=[
            Dependency("INV-11 Interface contract language", "upstream", "Defines the signatures being fingerprinted"),
            Dependency("INV-60 Wasm application fabric", "upstream", "Routes frames between hosts"),
            Dependency("INV-65 Capability providers", "downstream", "Receives provider calls in this format"),
            Dependency("INV-36 Control transport", "peer", "Seals control-class RPC frames")
        ],
        source_of_truth="The receiver's signature; a caller's frame is accepted only if its fingerprint matches it.",
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
            "Name interface, version and function in every frame",
            "Carry a signature fingerprint",
            "Refuse frames whose fingerprint does not match",
            "Return typed errors, not transport failures",
            "Enforce a deadline on every call"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Defining interfaces",
            "Encrypting transport",
            "Discovering services"
        ],
        interfaces={
            "frame": "PK_WRPC_FRAME/1 - interface, version, function, fingerprint, args",
            "error": "PK_WRPC_ERROR/1 - a typed error result",
            "deadline": "PK_WRPC_DEADLINE/1 - absolute call deadline"
        },
        threats=[
            "Silent argument misinterpretation after drift",
            "Calls hanging without deadline",
            "Transport errors masquerading as application errors"
        ],
        failure_modes=[
            "Signature mismatch",
            "Unknown function",
            "Deadline exceeded",
            "Callee trapped"
        ],
        slos=[
            Slo("no misreads", "zero frames decoded against a mismatched signature", "no budget"),
            Slo("deadlines", "zero calls outliving their deadline", "no budget"),
            Slo("overhead", "p99 framing overhead under 50us", "1% may exceed")
        ],
        signals={
            "calls": "counter by interface",
            "mismatches": "counter",
            "deadline_exceeded": "counter"
        },
    )
