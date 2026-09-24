"""Binding contract for INV-14 - Previous asynchronous model.

The previous asynchronous model is the poll-based one: a component hands the host a list of pollables and blocks until one is ready. It works, it is simple, and it does not compose -- which is exactly why the new ABI exists. This element keeps it running honestly while it is still deployed, and states what it cannot do.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-14"
ELEMENT_NAME = "Previous asynchronous model"


def build() -> Contract:
    """Return the production contract for INV-14."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the legacy poll-based async surface for components still using it: block on a pollable set with a bounded timeout, guarantee no lost readiness, and mark the model deprecated so nothing new is written against it."
        ),
        owns=[
            "The pollable set and its readiness semantics",
            "Bounded blocking with timeout",
            "Lost-wakeup prevention",
            "Deprecation status and migration reporting",
            "Refusal to compose a pollable across component boundaries"
        ],
        not_owns=[
            "The new asynchronous ABI",
            "Stream and future primitives",
            "Host I/O implementations",
            "Scheduling",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-13 System interface", "upstream", "Supplies the pollables this model waits on"),
            Dependency("INV-15 New asynchronous ABI", "downstream", "The migration target for this model"),
            Dependency("GAP-15 Runtime compatibility certification", "peer", "Certifies which runtimes still support it")
        ],
        source_of_truth="The pollable's own readiness flag; a poll returns a ready index or a timeout, never a guess.",
        assumptions=[
            "Existing components still use this model and cannot be rewritten overnight",
            "Pollables do not compose across component boundaries, which is the model's limit",
            "A blocking call with no timeout is an availability hazard"
        ],
        boundaries={
            "tenant": "pollables belong to one component instance of one tenant",
            "environment": "an environment may forbid this model for new components",
            "site": "supported wherever the legacy runtime is",
            "workload": "one pollable set per instance"
        },
        mandatory=[
            "Return a ready pollable or a timeout, never block unbounded",
            "Never lose a readiness signal that arrived during a poll",
            "Refuse to pass a pollable across a component boundary",
            "Report the model as deprecated on every use",
            "Report migration status per component"
        ],
        optional=[
            "Readiness batching",
            "Poll-set size hints",
            "Automatic migration shims"
        ],
        non_goals=[
            "Composing async across components",
            "Being the model new code is written against",
            "Replacing the new ABI",
            "Unbounded blocking"
        ],
        interfaces={
            "poll": "PK_POLL/1 - block on a pollable set with a timeout",
            "pollable": "PK_POLLABLE/1 - a readiness handle owned by one instance"
        },
        threats=[
            "A pollable smuggled across a component boundary aliasing another instance's state",
            "Lost wakeup stalling a component indefinitely",
            "Unbounded blocking used as a denial-of-service",
            "New components written against a deprecated model"
        ],
        failure_modes=[
            "Poll times out with nothing ready",
            "Pollable belongs to another instance",
            "Readiness arrives during the poll window",
            "Poll set is empty"
        ],
        slos=[
            Slo("no lost wakeups", "zero readiness signals dropped across a poll boundary", "no budget"),
            Slo("bounded blocking", "zero polls blocking past their timeout", "no budget"),
            Slo("migration visibility", "every use reports the deprecation and the migration target", "no budget")
        ],
        signals={
            "polls": "counter by outcome (ready, timeout)",
            "deprecated_uses": "counter by component",
            "cross_instance_refusals": "counter",
            "poll_set_size": "histogram"
        },
    )
