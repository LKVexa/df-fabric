"""Binding contract for INV-57 - Durable execution.

Durable execution makes a long-running workflow survive crashes by recording what happened rather than where the code was. Each activity's result goes into a history; after a crash the workflow code re-runs from the top and every completed activity returns its recorded result instead of running again. That only works if the workflow code is deterministic, so divergence from the history is detected and refused.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-57"
ELEMENT_NAME = "Durable execution"


def build() -> Contract:
    """Return the production contract for INV-57."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own durable workflows: event-sourced history, deterministic replay, once-only activity effects, and detection of non-deterministic workflow code."
        ),
        owns=[
            "The workflow history",
            "Deterministic replay",
            "Once-only activity execution",
            "Non-determinism detection",
            "Resumption after crash"
        ],
        not_owns=[
            "Activity business logic",
            "History storage backend",
            "Timers infrastructure",
            "Scheduling of workers",
            "Messaging"
        ],
        dependencies=[
            Dependency("INV-50 State abstraction", "upstream", "Stores the workflow history"),
            Dependency("INV-53 Message reliability", "upstream", "Delivers activity tasks at least once"),
            Dependency("INV-69 Agentic workload layer", "downstream", "Runs long agent plans as durable workflows"),
            Dependency("INV-56 Distributed stateful compute", "peer", "The other stateful model beside workflows")
        ],
        source_of_truth="The history; the workflow's in-memory state is always reconstructable from it and never the other way round.",
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
            "Record every activity result before continuing",
            "Replay completed activities from history",
            "Execute each activity's effect at most once",
            "Refuse replay that diverges from history",
            "Resume from the last recorded event after a crash"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Writing activities",
            "Storing history",
            "Scheduling workers"
        ],
        interfaces={
            "history": "PK_WF_HISTORY/1 - ordered activity events",
            "activity": "PK_WF_ACTIVITY/1 - a recorded unit of work",
            "replay": "PK_WF_REPLAY/1 - deterministic re-execution against history"
        },
        threats=[
            "Activity re-executed after crash, duplicating effects",
            "Non-deterministic code corrupting replay",
            "History lost"
        ],
        failure_modes=[
            "Non-determinism detected",
            "Activity failed",
            "History unavailable",
            "Workflow timed out"
        ],
        slos=[
            Slo("once-only effects", "zero activities executed twice across replays", "no budget"),
            Slo("determinism", "every divergence detected before effects", "no budget"),
            Slo("replay speed", "p99 replay of 1000 events under 100ms", "1% may exceed")
        ],
        signals={
            "workflows": "gauge by state",
            "replays": "counter",
            "nondeterminism": "counter",
            "activities_executed": "counter"
        },
    )
