"""Binding contract for INV-18 - Completion primitive.

The completion primitive is the one-shot counterpart to a stream: exactly one value, delivered once, to exactly one receiver. Having it as its own type rather than a stream of length one means the compiler knows there is no second value coming, so the receiver needs no loop and the writer cannot accidentally send twice.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-18"
ELEMENT_NAME = "Completion primitive"


def build() -> Contract:
    """Return the production contract for INV-18."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own one-shot value delivery: a future handle that resolves at most once, an explicit error resolution, and the refusal of a second resolution or a second receiver."
        ),
        owns=[
            "Future handle allocation and typing",
            "At-most-once resolution",
            "Error resolution as a first-class outcome",
            "Single-receiver enforcement",
            "Abandonment detection when the writer is dropped unresolved"
        ],
        not_owns=[
            "Many-valued flow",
            "The subtask table",
            "Retry policy",
            "Transport",
            "Payload meaning"
        ],
        dependencies=[
            Dependency("INV-15 New asynchronous ABI", "upstream", "Future readiness is reported through waitable sets"),
            Dependency("INV-12 Language interoperability", "upstream", "Lowers and lifts the resolved value"),
            Dependency("INV-17 Streaming primitive", "peer", "The many-shot counterpart to this primitive"),
            Dependency("INV-20 HTTP component worlds", "downstream", "Trailers and status resolve as completions"),
            Dependency("INV-16 Async component functions", "downstream", "An async function's return is a completion")
        ],
        source_of_truth="The resolution record; once written it is immutable, and every later attempt is an error rather than an overwrite.",
        assumptions=[
            "Exactly one value will be produced, or an error will be",
            "A writer may be dropped before resolving",
            "Two receivers for one value is a modelling error, not a feature"
        ],
        boundaries={
            "tenant": "a future never spans a tenant boundary without explicit transfer",
            "environment": "abandonment timeouts differ per environment",
            "site": "future handles are instance-local",
            "workload": "outstanding futures count against the workload's budget"
        },
        mandatory=[
            "Resolve at most once",
            "Treat an error resolution as a normal outcome, not an exception path",
            "Refuse a second receiver",
            "Report abandonment when a writer is dropped unresolved",
            "Type the resolved value"
        ],
        optional=[
            "Chained futures",
            "Timeout-driven automatic error resolution",
            "Value transfer without copy inside one instance"
        ],
        non_goals=[
            "Carrying many values",
            "Retrying the producer",
            "Broadcasting to several receivers",
            "Allowing a resolution to be overwritten"
        ],
        interfaces={
            "future": "PK_FUTURE/1 - a typed one-shot handle",
            "resolve": "PK_FUTURE_RESOLVE/1 - value or error resolution",
            "abandon": "PK_FUTURE_ABANDON/1 - writer dropped without resolving"
        },
        threats=[
            "A second resolution overwriting the first",
            "Two receivers racing for one value",
            "A dropped writer leaving a receiver waiting forever",
            "An error resolution mistaken for a value"
        ],
        failure_modes=[
            "Already resolved",
            "Already taken",
            "Abandoned by the writer",
            "Value type mismatch"
        ],
        slos=[
            Slo("at most once", "zero futures resolved twice", "no budget"),
            Slo("no orphans", "every abandoned future raises on the receiver", "no budget"),
            Slo("resolution cost", "p99 resolution delivery under 1us within an instance", "1% may exceed")
        ],
        signals={
            "futures_open": "gauge by value type",
            "double_resolutions": "counter, expected to stay at zero",
            "abandonments": "counter by reason",
            "error_resolutions": "counter by error kind"
        },
    )
