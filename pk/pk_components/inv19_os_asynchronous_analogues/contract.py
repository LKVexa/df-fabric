"""Binding contract for INV-19 - OS asynchronous analogues.

OS asynchronous analogues are the mapping between the component world's streams and futures and what the host operating system actually offers -- epoll, kqueue, io_uring, IOCP. Each has a different shape (readiness versus completion), and the mapping has to be honest about which, because a readiness API pretending to be a completion API loses errors.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-19"
ELEMENT_NAME = "OS asynchronous analogues"


def build() -> Contract:
    """Return the production contract for INV-19."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the host-side asynchronous backend: detect the available mechanism, map readiness or completion semantics onto stream credit and future resolution, and degrade to a portable fallback without changing observable behaviour."
        ),
        owns=[
            "Backend detection and selection",
            "Readiness-to-credit mapping",
            "Completion-to-future mapping",
            "The portable fallback backend",
            "Per-backend error translation into component-world errors"
        ],
        not_owns=[
            "Stream and future semantics",
            "The async ABI",
            "Guest code",
            "Scheduling policy",
            "Kernel behaviour"
        ],
        dependencies=[
            Dependency("INV-17 Streaming primitive", "upstream", "Defines the credit semantics being fed"),
            Dependency("INV-18 Completion primitive", "upstream", "Defines the future semantics being resolved"),
            Dependency("INV-15 New asynchronous ABI", "upstream", "Readiness is surfaced through waitable sets"),
            Dependency("INV-13 System interface", "downstream", "Host calls reach the OS through these backends"),
            Dependency("SCH-01 Multi-runtime scheduler", "peer", "Consumes backend readiness to pick runnable work")
        ],
        source_of_truth="The backend's own semantics class (readiness or completion); the mapping adapts to it and never pretends one is the other.",
        assumptions=[
            "The available mechanism differs by kernel and by build",
            "Readiness and completion are genuinely different models",
            "Observable component behaviour must not depend on which backend is in use"
        ],
        boundaries={
            "tenant": "backend resources are partitioned per tenant",
            "environment": "backend availability is an environment property",
            "site": "different sites may run different kernels",
            "workload": "descriptor budgets are per workload"
        },
        mandatory=[
            "Detect the available backend rather than assuming one",
            "Classify each backend as readiness or completion and map accordingly",
            "Provide a portable fallback that is always available",
            "Keep observable component behaviour identical across backends",
            "Translate backend errors into component-world errors"
        ],
        optional=[
            "Backend-specific batching",
            "Registered buffers where the backend supports them",
            "Runtime backend switching"
        ],
        non_goals=[
            "Reimplementing kernel interfaces",
            "Exposing backend detail to guests",
            "Choosing scheduling policy",
            "Pretending a readiness API reports completion errors"
        ],
        interfaces={
            "backend": "PK_ASYNC_BACKEND/1 - the selected mechanism and its semantics class",
            "arm": "PK_ASYNC_ARM/1 - arm a descriptor for readiness or submit a completion",
            "reap": "PK_ASYNC_REAP/1 - collect readiness or completion events"
        },
        threats=[
            "Backend error swallowed because the mapping assumed the wrong model",
            "Descriptor exhaustion from an unbounded arm rate",
            "A guest inferring the host kernel from timing",
            "Fallback silently used where the fast path was expected"
        ],
        failure_modes=[
            "No backend available",
            "Descriptor budget exhausted",
            "Backend returned an error the mapping cannot classify",
            "Fallback engaged"
        ],
        slos=[
            Slo("behavioural identity", "identical component-visible outcomes on every backend", "no budget"),
            Slo("fallback availability", "the portable backend is available 100% of the time", "no budget"),
            Slo("reap latency", "p99 event reaped within 1 scheduler tick of readiness", "1% may exceed")
        ],
        signals={
            "backend_selected": "gauge, labelled by backend name and semantics class",
            "fallback_engagements": "counter by reason",
            "reap_events": "counter by backend",
            "untranslatable_errors": "counter, expected to stay at zero"
        },
    )
