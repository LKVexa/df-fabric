"""Binding contract for GAP-12 - WAN resilience and NAT traversal.

WAN resilience and NAT traversal is the plumbing that keeps an edge site reachable from behind a carrier-grade NAT on a flaky link. It escalates through connection strategies in cost order, backs off honestly, and reports the link as down rather than pretending a stale path still works.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-12"
ELEMENT_NAME = "WAN resilience and NAT traversal"


def build() -> Contract:
    """Return the production contract for GAP-12."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own reachability to and from edge sites across hostile networks: escalate through direct, hole-punched and relayed paths in cost order, apply bounded exponential backoff, and report a partition rather than masking it."
        ),
        owns=[
            "Connection strategy escalation and its order",
            "NAT traversal attempts and their outcomes",
            "Backoff schedule and its bounds",
            "Path health and the partition verdict",
            "Relay fallback and its cost accounting"
        ],
        not_owns=[
            "Transport encryption",
            "Data replication semantics",
            "Autonomy policy during partition",
            "Application protocols",
            "Relay infrastructure provisioning"
        ],
        dependencies=[
            Dependency("GAP-06 Device identity and attestation", "upstream", "Identifies the peer before a path is used"),
            Dependency("GAP-04 Disconnected-operation controller", "downstream", "Consumes the partition verdict"),
            Dependency("PLN-06 Data plane", "downstream", "Uses the established path for bulk transfer"),
            Dependency("GAP-09 Unified observability", "downstream", "Receives path and backoff signals")
        ],
        source_of_truth="The most recent successful probe on a path; an untested path is not a working path.",
        assumptions=[
            "Many edge sites sit behind symmetric NAT where hole punching fails",
            "Relays cost money and bandwidth, so they are a last resort",
            "A link may be up but unusable for bulk traffic"
        ],
        boundaries={
            "tenant": "paths are site-level infrastructure, never tenant-specific",
            "environment": "relay pools differ per environment",
            "site": "each site pair has its own path state",
            "workload": "workloads use paths but never select them"
        },
        mandatory=[
            "Try connection strategies in declared cost order",
            "Apply bounded exponential backoff between attempts",
            "Report a partition when every strategy is exhausted",
            "Never report a path healthy without a recent successful probe",
            "Fall back to relay only after cheaper strategies fail"
        ],
        optional=[
            "Path quality scoring beyond up/down",
            "Multi-path striping",
            "Predictive relay pre-warming"
        ],
        non_goals=[
            "Encrypting traffic",
            "Provisioning relays",
            "Deciding what to do during a partition",
            "Guaranteeing connectivity through a severed link"
        ],
        interfaces={
            "connect": "PK_PATH_REQUEST/1 - establish a path to a peer site",
            "path": "PK_PATH_STATE/1 - current strategy, health and last successful probe",
            "backoff": "PK_BACKOFF/1 - the current retry schedule and its bound"
        },
        threats=[
            "A hostile relay observing or altering traffic",
            "Backoff exhaustion used as a denial-of-service",
            "Path state forgery presenting a partition as healthy",
            "Relay billing abuse by forcing relay fallback"
        ],
        failure_modes=[
            "All strategies exhausted",
            "Symmetric NAT defeats hole punching",
            "Relay unavailable",
            "Probe succeeds but bulk transfer fails"
        ],
        slos=[
            Slo("path honesty", "zero paths reported healthy without a probe inside the freshness window", "no budget"),
            Slo("escalation order", "zero relay fallbacks before cheaper strategies were tried", "no budget"),
            Slo("backoff bound", "retry interval never exceeds the declared ceiling", "no budget")
        ],
        signals={
            "path_strategy": "current strategy per site pair",
            "traversal_attempts": "counter by strategy and outcome",
            "backoff_seconds": "gauge of the current retry interval",
            "relay_bytes": "counter of bytes carried over relays",
            "partitions_declared": "counter of site pairs declared partitioned"
        },
    )
