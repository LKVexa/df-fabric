"""Binding contract for INV-20 - HTTP component worlds.

An HTTP component world is the smallest useful thing a serverless component can be: a world that imports an outgoing-request capability and exports an incoming-request handler, with both bodies as streams and trailers as completions. Because the world is explicit, a component that was never granted outgoing HTTP simply cannot make a call.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-20"
ELEMENT_NAME = "HTTP component worlds"


def build() -> Contract:
    """Return the production contract for INV-20."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the HTTP world definition and its enforcement: the handler export, the outgoing capability import, body streaming, trailer completion, and refusal of any egress the world did not grant."
        ),
        owns=[
            "The incoming-handler export shape",
            "The outgoing-request capability import",
            "Request and response bodies as streams",
            "Trailers as completions",
            "Egress allow-listing per world"
        ],
        not_owns=[
            "TLS termination",
            "Routing between components",
            "Transport implementation",
            "Business logic",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-11 Interface contract language", "upstream", "Defines the world and its types"),
            Dependency("INV-17 Streaming primitive", "upstream", "Bodies are streams"),
            Dependency("INV-18 Completion primitive", "upstream", "Trailers and status are completions"),
            Dependency("INV-13 System interface", "upstream", "Egress is a granted capability"),
            Dependency("INV-21 Local service chaining", "downstream", "Chains handlers without leaving the host"),
            Dependency("INV-16 Async component functions", "peer", "The handler is an async component function")
        ],
        source_of_truth="The world definition; a capability absent from it does not exist for that component, whatever the guest attempts.",
        assumptions=[
            "Most serverless workloads are request/response over HTTP",
            "Bodies can be far larger than memory",
            "A component's egress must be reviewable before it runs"
        ],
        boundaries={
            "tenant": "egress allow-lists are per tenant",
            "environment": "allowed hosts differ per environment",
            "site": "the world shape is site-independent",
            "workload": "concurrency and body limits are per workload"
        },
        mandatory=[
            "Export exactly one incoming-request handler per world",
            "Import outgoing HTTP only when the world grants it",
            "Carry bodies as streams rather than buffers",
            "Deliver trailers as a completion",
            "Refuse an outgoing request to a host the world did not allow"
        ],
        optional=[
            "Response caching",
            "Automatic decompression",
            "Connection pooling across invocations"
        ],
        non_goals=[
            "Implementing TLS",
            "Routing",
            "Owning the HTTP transport",
            "Buffering whole bodies in memory"
        ],
        interfaces={
            "handler": "PK_HTTP_HANDLER/1 - the exported incoming-request function",
            "outgoing": "PK_HTTP_OUTGOING/1 - the imported egress capability",
            "body": "PK_HTTP_BODY/1 - a request or response body as a stream"
        },
        threats=[
            "Data exfiltration through unrestricted egress",
            "Whole-body buffering exhausting memory",
            "SSRF to host-internal addresses",
            "Trailers used to smuggle fields past a reviewed header set"
        ],
        failure_modes=[
            "Egress denied by the world",
            "Body exceeded its limit",
            "Upstream unreachable",
            "Handler trapped mid-response"
        ],
        slos=[
            Slo("egress containment", "zero requests to hosts outside the world's allow-list", "no budget"),
            Slo("streaming", "no body fully buffered before forwarding", "no budget"),
            Slo("handler latency", "p99 handler dispatch under 1ms excluding user code", "1% may exceed")
        ],
        signals={
            "requests_handled": "counter by status class",
            "egress_denials": "counter by attempted host",
            "body_bytes": "histogram by direction",
            "trailer_resolutions": "counter by outcome"
        },
    )
