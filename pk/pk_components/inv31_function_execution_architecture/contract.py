"""Binding contract for INV-31 - Function execution architecture.

The function execution architecture is the request-scoped end of the spectrum: an invocation gets an instance, does one job, and the instance is either recycled within its tenant or destroyed. Everything hard about it is the reuse decision, so that is what this element owns.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-31"
ELEMENT_NAME = "Function execution architecture"


def build() -> Contract:
    """Return the production contract for INV-31."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own function-instance lifecycle around a single invocation: decide warm reuse versus cold start under a strict same-tenant-same-version rule, bound concurrency per instance, and destroy instances rather than leaking state between invocations."
        ),
        owns=[
            "Function instance pool and its reuse rule",
            "Warm-versus-cold decision",
            "Per-instance concurrency bound",
            "Invocation-scoped state clearing",
            "Instance eviction and maximum age"
        ],
        not_owns=[
            "The isolation tier beneath",
            "Capacity targets",
            "Routing or load balancing",
            "Function source code",
            "Placement"
        ],
        dependencies=[
            Dependency("PLN-04 Execution plane", "upstream", "Supplies the isolation tier each instance runs in"),
            Dependency("INV-26 MicroVM snapshotting", "upstream", "Makes a cold start cheap enough to prefer over risky reuse"),
            Dependency("PLN-05 Elasticity plane", "downstream", "Scales the pool this element draws from"),
            Dependency("GAP-09 Unified observability", "downstream", "Receives cold/warm and concurrency signals")
        ],
        source_of_truth="The instance's recorded tenant and code version; reuse is permitted only on an exact match of both.",
        assumptions=[
            "A warm instance retains memory from its previous invocation",
            "A cold start is slower but always safe",
            "Concurrency inside one instance shares mutable state"
        ],
        boundaries={
            "tenant": "an instance is never reused across tenants",
            "environment": "reuse policy and max age differ per environment",
            "site": "pools are per site and do not migrate",
            "workload": "one function version per instance"
        },
        mandatory=[
            "Reuse an instance only for the same tenant and the same code version",
            "Clear invocation-scoped state between invocations",
            "Bound concurrent invocations per instance",
            "Evict instances past their maximum age",
            "Report whether each invocation was cold or warm"
        ],
        optional=[
            "Pre-warming within a tenant",
            "Snapshot-backed cold starts",
            "Adaptive pool sizing"
        ],
        non_goals=[
            "Cross-tenant instance sharing",
            "Routing invocations",
            "Guaranteeing warm starts",
            "Persisting state between invocations"
        ],
        interfaces={
            "invoke": "PK_INVOCATION/1 - run one invocation, cold or warm",
            "pool": "PK_FUNCTION_POOL/1 - instances, their tenant, version and age"
        },
        threats=[
            "State leaking between invocations of different tenants",
            "Version skew serving an old code version from a warm instance",
            "Concurrency inside one instance corrupting shared state",
            "Instance age used to accumulate data across many invocations"
        ],
        failure_modes=[
            "No warm instance available",
            "Instance exceeded its maximum age",
            "Concurrency bound reached",
            "Version mismatch on a warm instance"
        ],
        slos=[
            Slo("tenant isolation", "zero instances reused across tenants", "no budget"),
            Slo("version fidelity", "zero invocations served by an instance on a different code version", "no budget"),
            Slo("warm rate", "at least 80% warm invocations in steady state", "20% may be cold")
        ],
        signals={
            "invocations": "counter by cold/warm and outcome",
            "pool_instances": "gauge by tenant, version and state",
            "instance_age_seconds": "histogram at eviction",
            "concurrency_rejections": "counter of invocations refused at the per-instance bound",
            "state_clears": "counter of invocation-scoped clears performed"
        },
    )
