"""Binding contract for INV-17 - Streaming primitive.

The streaming primitive carries many values over time through one typed handle. What makes it worth having as a primitive rather than a convention is that backpressure, end-of-stream and the reader's disappearance are all part of the type -- a writer that ignores a closed reader gets an error, not a silently discarded value.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-17"
ELEMENT_NAME = "Streaming primitive"


def build() -> Contract:
    """Return the production contract for INV-17."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the stream handle: typed element flow, credit-based backpressure, explicit end-of-stream, and the errors a dropped end produces on the other side."
        ),
        owns=[
            "Stream handle allocation and typing",
            "Credit-based backpressure between writer and reader",
            "Explicit end-of-stream signalling",
            "Dropped-end detection and error delivery",
            "Buffer bounds for a stream in flight"
        ],
        not_owns=[
            "One-shot value delivery",
            "The subtask table",
            "Transport encoding",
            "Scheduling of readers and writers",
            "Payload semantics"
        ],
        dependencies=[
            Dependency("INV-15 New asynchronous ABI", "upstream", "Stream readiness is reported through waitable sets"),
            Dependency("INV-12 Language interoperability", "upstream", "Lowers and lifts stream elements"),
            Dependency("INV-18 Completion primitive", "peer", "The one-shot counterpart to this many-shot primitive"),
            Dependency("INV-20 HTTP component worlds", "downstream", "Request and response bodies are streams"),
            Dependency("INV-19 OS asynchronous analogues", "downstream", "Maps OS readiness onto stream credit")
        ],
        source_of_truth="The credit counter held by the reader; a writer's belief about available space is advisory until credit is granted.",
        assumptions=[
            "A reader can be slower than its writer, indefinitely",
            "Either end may disappear at any time",
            "Unbounded buffering is a memory-exhaustion bug, not a feature"
        ],
        boundaries={
            "tenant": "a stream never spans a tenant boundary without an explicit transfer",
            "environment": "buffer bounds differ per environment",
            "site": "stream handles are instance-local",
            "workload": "credit limits are per workload"
        },
        mandatory=[
            "Type every stream and refuse a mismatched element",
            "Grant credit explicitly; never let a writer outrun its reader",
            "Bound the in-flight buffer",
            "Signal end-of-stream explicitly rather than by silence",
            "Deliver an error when the far end has been dropped"
        ],
        optional=[
            "Credit batching to reduce round trips",
            "Zero-copy element handoff within one instance",
            "Stream splicing between two components"
        ],
        non_goals=[
            "Unbounded buffering",
            "Inferring end-of-stream from a timeout",
            "Carrying one-shot values",
            "Defining what the elements mean"
        ],
        interfaces={
            "stream": "PK_STREAM/1 - a typed stream handle with reader and writer ends",
            "credit": "PK_STREAM_CREDIT/1 - credit granted by the reader",
            "close": "PK_STREAM_CLOSE/1 - explicit end-of-stream or drop"
        },
        threats=[
            "Unbounded buffering exhausting host memory",
            "A writer continuing after the reader is gone",
            "Type confusion putting the wrong element on a stream",
            "End-of-stream lost, leaving a reader waiting forever"
        ],
        failure_modes=[
            "Credit exhausted",
            "Far end dropped",
            "Element type mismatch",
            "Stream closed while elements were still buffered"
        ],
        slos=[
            Slo("bounded memory", "in-flight buffer never exceeds granted credit", "no budget"),
            Slo("drop detection", "a write after a drop errors on the first attempt", "no budget"),
            Slo("element cost", "p99 element handoff under 1us within an instance", "1% may exceed")
        ],
        signals={
            "streams_open": "gauge by element type",
            "credit_stalls": "counter of writes blocked for credit",
            "dropped_end_errors": "counter by which end dropped",
            "elements_transferred": "counter by stream"
        },
    )
