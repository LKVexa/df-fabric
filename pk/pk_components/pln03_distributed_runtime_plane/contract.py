"""Binding contract for PLN-03 - Distributed runtime plane.

The distributed runtime plane provides the sidecar-free building blocks an application uses at run time: state, messaging, secrets, and service invocation, behind stable APIs with pluggable backing infrastructure. Applications bind to capabilities, never to a broker or a database.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-03"
ELEMENT_NAME = "Distributed runtime plane"


def build() -> Contract:
    """Return the production contract for PLN-03."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the stable distributed-runtime API surface (state, messaging, secrets, invocation) and the adapter layer that binds each capability to concrete infrastructure without leaking the backend into the application."
        ),
        owns=[
            "The state, messaging, secrets, and invocation APIs",
            "Adapter registration and lifecycle",
            "At-least-once delivery and idempotency keys",
            "Capability-scoped access to each backing store",
            "Backend-independence of the API contract"
        ],
        not_owns=[
            "Backing store implementations",
            "Application business logic",
            "Placement of the runtime",
            "Transport-layer security primitives",
            "Durable workflow semantics"
        ],
        dependencies=[
            Dependency("PLN-02 Application plane", "upstream", "Supplies the resolved revision and its capability bindings"),
            Dependency("INV-49 Pluggable infrastructure adapters", "upstream", "Supplies the concrete adapters"),
            Dependency("PLN-04 Execution plane", "downstream", "Hosts the runtime alongside the workload"),
            Dependency("PLN-06 Data plane", "downstream", "Carries bulk payloads the runtime does not inline"),
            Dependency("PLN-07 Security plane", "peer", "Issues the capability tokens the runtime enforces")
        ],
        source_of_truth="The capability bindings recorded in the application revision; adapters may not be rebound at run time.",
        assumptions=[
            "A backing store may be unavailable without the application being at fault",
            "Message delivery is at-least-once, so consumers must be idempotent",
            "Secrets are fetched, never embedded in the revision"
        ],
        boundaries={
            "tenant": "every adapter call is tenant-scoped; keys are namespaced per tenant",
            "environment": "adapters differ per environment and are bound at resolution",
            "site": "a site may run a local adapter for the same capability",
            "workload": "capability tokens are issued per workload, not per node"
        },
        mandatory=[
            "Expose state, messaging, secrets, and invocation behind backend-independent APIs",
            "Enforce the capability bindings from the revision at every call",
            "Namespace all keys and topics by tenant",
            "Provide idempotency keys for at-least-once delivery",
            "Fail closed when a capability token is absent or expired"
        ],
        optional=[
            "Adapter-level caching",
            "Local-first adapters for disconnected sites",
            "Batch invocation"
        ],
        non_goals=[
            "Implementing brokers or databases",
            "Guaranteeing exactly-once delivery",
            "Cross-tenant data access under any configuration",
            "Durable multi-step workflow execution"
        ],
        interfaces={
            "state": "PK_STATE/1 - get, set, delete, transact within a tenant namespace",
            "messaging": "PK_MESSAGE/1 - publish and subscribe with idempotency keys",
            "secrets": "PK_SECRET/1 - fetch a secret by capability-scoped reference",
            "invoke": "PK_INVOKE/1 - address another component by name, not by network location"
        },
        threats=[
            "A workload reaching a capability it was never bound to",
            "Key namespace escape reaching another tenant's state",
            "A hostile adapter exfiltrating payloads",
            "Replay of a message whose idempotency key was not honoured",
            "Secret material captured in logs or traces"
        ],
        failure_modes=[
            "Backing store unavailable",
            "Capability token expired mid-call",
            "Duplicate delivery of a message",
            "Adapter returns a payload larger than the inline limit"
        ],
        slos=[
            Slo("state latency", "p99 state get under 10ms against a local adapter", "1% may exceed"),
            Slo("capability enforcement", "zero calls served without a matching binding", "no budget"),
            Slo("delivery", "at-least-once delivery for every accepted publish", "0.01% may require redelivery beyond the retry window")
        ],
        signals={
            "adapter_calls": "counter by capability, adapter, and outcome",
            "capability_denials": "counter of calls refused for missing or expired bindings",
            "state_latency_seconds": "histogram per capability",
            "duplicate_deliveries": "counter of messages suppressed by idempotency key"
        },
    )
