"""Binding contract for INV-16 - Async component functions.

Async component functions are the guest-visible shape of the new ABI: a function declared async in the interface may return before its work is finished, and the caller decides whether to wait. The hard part is composition -- a sync caller of an async callee must still be correct, and re-entrancy must not corrupt the callee's state.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-16"
ELEMENT_NAME = "Async component functions"


def build() -> Contract:
    """Return the production contract for INV-16."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the guest-facing async function surface: declaration, the sync/async call matrix, re-entrancy rules and the state machine each async function is compiled into."
        ),
        owns=[
            "Async function declaration and lifting",
            "The sync-caller/async-callee bridging rules",
            "Re-entrancy admission for an in-flight instance",
            "Per-call state machine storage",
            "Return-value delivery on completion"
        ],
        not_owns=[
            "Subtask handle mechanics",
            "Stream and completion payloads",
            "Scheduling",
            "Host I/O",
            "Interface syntax"
        ],
        dependencies=[
            Dependency("INV-15 New asynchronous ABI", "upstream", "Supplies subtask handles and waitable sets"),
            Dependency("INV-11 Interface contract language", "upstream", "Declares which functions are async"),
            Dependency("INV-17 Streaming primitive", "downstream", "Async functions are how streams are consumed"),
            Dependency("INV-20 HTTP component worlds", "downstream", "Handler functions are async component functions"),
            Dependency("INV-10 Component composition system", "peer", "Links async callers to async callees")
        ],
        source_of_truth="The interface declaration; whether a function is async is fixed at build time and never inferred at run time.",
        assumptions=[
            "A sync caller may legitimately call an async callee",
            "An instance may be re-entered while a call is in flight",
            "Each in-flight call needs its own state, not the instance's"
        ],
        boundaries={
            "tenant": "call state is per-instance, never shared",
            "environment": "re-entrancy limits differ per environment",
            "site": "async-ness is a build-time property, identical everywhere",
            "workload": "concurrency limit is per workload"
        },
        mandatory=[
            "Fix async-ness at build time from the interface declaration",
            "Allow a sync caller to call an async callee correctly",
            "Give every in-flight call its own state",
            "Refuse re-entrancy that would corrupt callee state",
            "Deliver the return value exactly once"
        ],
        optional=[
            "Automatic sync shims",
            "Re-entrancy queueing rather than refusal",
            "Inlining for callees that always complete immediately"
        ],
        non_goals=[
            "Inferring async-ness at run time",
            "Owning the subtask table",
            "Making every function async",
            "Sharing state between in-flight calls"
        ],
        interfaces={
            "declare": "PK_ASYNC_DECL/1 - build-time async-ness of a function",
            "invoke": "PK_ASYNC_INVOKE/1 - a call carrying its own state machine",
            "reentrancy": "PK_REENTRANCY/1 - admission decision for a re-entrant call"
        },
        threats=[
            "Re-entrancy corrupting callee state mid-call",
            "State shared between in-flight calls leaking data",
            "A return value delivered twice",
            "Async-ness changed at run time to bypass a caller's assumptions"
        ],
        failure_modes=[
            "Re-entrancy refused",
            "Concurrency limit reached",
            "Callee trapped with calls in flight",
            "Return delivered after cancellation"
        ],
        slos=[
            Slo("state isolation", "zero bytes of call state shared between in-flight calls", "no budget"),
            Slo("exactly once", "every completed call delivers its value exactly once", "no budget"),
            Slo("bridge cost", "p99 sync-caller bridging under 5us", "1% may exceed")
        ],
        signals={
            "calls_in_flight": "gauge per function",
            "reentrancy_refusals": "counter by function",
            "bridge_calls": "counter of sync-caller/async-callee pairs",
            "double_delivery": "counter, expected to stay at zero"
        },
    )
