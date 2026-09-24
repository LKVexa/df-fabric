"""Binding contract for INV-48 - Service communication APIs.

Service communication APIs are how one application calls another by name: resolve the name, carry the caller's identity, apply a timeout, and retry only when the operation is safe to repeat. The discipline is in the retry -- a non-idempotent call retried after a timeout can charge a card twice, so retries are keyed and deduplicated at the callee.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-48"
ELEMENT_NAME = "Service communication APIs"


def build() -> Contract:
    """Return the production contract for INV-48."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own service-to-service invocation: name resolution, identity propagation, timeouts, idempotency-keyed retries with backoff, and callee-side deduplication."
        ),
        owns=[
            "Service name resolution",
            "Caller identity propagation",
            "Per-call timeouts",
            "Idempotency-keyed retries with bounded backoff",
            "Callee-side deduplication"
        ],
        not_owns=[
            "Transport encryption",
            "Authorization decisions",
            "Service discovery registries",
            "Business semantics",
            "Load balancing policy"
        ],
        dependencies=[
            Dependency("INV-46 Distributed application runtime", "upstream", "Routes invocation through its invoke block"),
            Dependency("INV-47 Dapr deployment model", "upstream", "Guarantees a reachable local runtime"),
            Dependency("INV-59 Application authorization", "downstream", "Decides on the propagated identity"),
            Dependency("INV-58 Existing service-mesh layer", "peer", "May also retry; retries must not multiply")
        ],
        source_of_truth="The callee's deduplication record for an idempotency key; a caller's retry count is not evidence of how often work ran.",
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
            "Resolve services by logical name",
            "Propagate caller identity on every call",
            "Apply a timeout to every call",
            "Retry only keyed calls, with bounded backoff",
            "Execute a keyed operation at most once at the callee"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Encrypting transport",
            "Deciding authorization",
            "Running a registry"
        ],
        interfaces={
            "invoke": "PK_SVC_INVOKE/1 - a named call with identity and idempotency key",
            "resolve": "PK_SVC_RESOLVE/1 - logical name to endpoint",
            "policy": "PK_SVC_RESILIENCY/1 - timeout, retry and backoff"
        },
        threats=[
            "Retry storm amplifying an outage",
            "Duplicate side effects from retries",
            "Identity dropped between hops",
            "Unbounded waits pinning callers"
        ],
        failure_modes=[
            "Name unresolvable",
            "Timeout",
            "Retries exhausted",
            "Duplicate suppressed"
        ],
        slos=[
            Slo("exactly-once effects", "zero keyed operations executed twice", "no budget"),
            Slo("bounded retries", "no call retried more than its policy allows", "no budget"),
            Slo("latency", "p99 invocation overhead under 2ms", "1% may exceed")
        ],
        signals={
            "calls": "counter by service",
            "retries": "counter",
            "duplicates_suppressed": "counter",
            "timeouts": "counter"
        },
    )
