"""Binding contract for INV-15 - New asynchronous ABI.

The new asynchronous ABI is what lets a component wait without pinning anything. Instead of a pollable that only its own instance may look at, a call returns either a value or a subtask handle, and the host owns the readiness table. Because waiting is expressed as a handle rather than a blocked stack, a waiting component costs a table row instead of a thread.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-15"
ELEMENT_NAME = "New asynchronous ABI"


def build() -> Contract:
    """Return the production contract for INV-15."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the asynchronous calling convention: subtask handles, the waitable-set primitive, cancellation propagation, and the guarantee that no guest stack is blocked while a call is outstanding."
        ),
        owns=[
            "Subtask handle allocation and lifetime",
            "Waitable sets and their readiness reporting",
            "Cancellation propagation from caller to subtask",
            "Backpressure when a component exceeds its outstanding-call budget",
            "The guarantee that waiting consumes no guest stack"
        ],
        not_owns=[
            "The interface definitions being called",
            "Stream and completion payload semantics",
            "Host I/O implementations",
            "Scheduling policy",
            "Language bindings"
        ],
        dependencies=[
            Dependency("INV-11 Interface contract language", "upstream", "Declares which functions are async"),
            Dependency("INV-12 Language interoperability", "upstream", "Lowers and lifts the values a subtask returns"),
            Dependency("INV-14 Previous asynchronous model", "upstream", "The model being replaced; supplies the migration surface"),
            Dependency("INV-16 Async component functions", "downstream", "Expresses guest-visible async functions over this ABI"),
            Dependency("INV-17 Streaming primitive", "downstream", "Builds streams on subtask readiness"),
            Dependency("INV-18 Completion primitive", "downstream", "Builds one-shot completions on subtask readiness"),
            Dependency("SCH-01 Multi-runtime scheduler", "peer", "Decides when a ready subtask is actually resumed")
        ],
        source_of_truth="The host-side waitable table; a guest's view of readiness is a projection of it and is never authoritative.",
        assumptions=[
            "A component may have many calls outstanding at once",
            "Waiting must not cost a stack, thread or core",
            "A caller that goes away must not leave a subtask running forever"
        ],
        boundaries={
            "tenant": "waitable tables are per-instance and never shared across tenants",
            "environment": "budget sizes differ per environment",
            "site": "handles are meaningless outside the instance that owns them",
            "workload": "outstanding-call budget is per workload"
        },
        mandatory=[
            "Return a subtask handle for every call that does not complete immediately",
            "Report readiness only through the host-owned waitable table",
            "Propagate cancellation from caller to every outstanding subtask",
            "Refuse a new call once the outstanding budget is exhausted",
            "Never block a guest stack while a call is outstanding"
        ],
        optional=[
            "Eager completion when the callee returns synchronously",
            "Priority hints on waitable sets",
            "Batched readiness delivery"
        ],
        non_goals=[
            "Implementing host I/O",
            "Choosing a scheduling policy",
            "Defining stream semantics",
            "Preserving the old pollable's instance-local shape"
        ],
        interfaces={
            "call": "PK_ASYNC_CALL/1 - returns a value or a subtask handle",
            "wait": "PK_WAITABLE_SET/1 - a set of subtask handles and their readiness",
            "cancel": "PK_SUBTASK_CANCEL/1 - cancellation of an outstanding subtask"
        },
        threats=[
            "Handle forgery letting one instance wait on another's subtask",
            "Unbounded outstanding calls exhausting host memory",
            "Cancellation ignored, leaving work running after the caller is gone",
            "Lost wakeup stalling a component indefinitely"
        ],
        failure_modes=[
            "Outstanding-call budget exhausted",
            "Subtask cancelled before completion",
            "Handle used after it was consumed",
            "Callee trapped mid-subtask"
        ],
        slos=[
            Slo("no blocked stacks", "zero guest stacks blocked on an outstanding call", "no budget"),
            Slo("cancellation", "p99 cancellation acknowledged within 1 scheduler tick", "1% may exceed"),
            Slo("wait cost", "a waiting component holds one table row and no thread", "no budget")
        ],
        signals={
            "subtasks_open": "gauge of outstanding subtasks per instance",
            "budget_refusals": "counter of calls refused for budget",
            "cancellations": "counter by reason",
            "wait_latency_ticks": "histogram from readiness to resume"
        },
    )
