"""Binding contract for PLN-01 - Intent plane.

The intent plane holds the desired state of the estate as a live graph rather than as disconnected Terraform state and Kubernetes YAML. It accepts declarations, resolves them into a dependency-ordered reconciliation plan, and hands that plan to the planes below. It never executes: planning and execution are deliberately separated.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-01"
ELEMENT_NAME = "Intent plane"


def build() -> Contract:
    """Return the production contract for PLN-01."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the authoritative desired-state graph for the estate, admit or reject declarations against policy, and emit a dependency-ordered, dry-runnable reconciliation plan for downstream planes to execute."
        ),
        owns=[
            "The desired-state graph and its schema",
            "Declaration admission and validation",
            "Dependency resolution and plan ordering",
            "Drift detection against reported actual state",
            "Plan versioning, diffing, and rollback targets"
        ],
        not_owns=[
            "Execution of any plan step",
            "Workload placement decisions",
            "Runtime or node lifecycle",
            "Data-plane transport",
            "Secret material"
        ],
        dependencies=[
            Dependency("PLN-07 Security plane", "upstream", "Admission policy and identity for declaration authors"),
            Dependency("GAP-13 Policy engine", "upstream", "Policy evaluation for admission decisions"),
            Dependency("PLN-02 Application plane", "downstream", "Consumes the reconciliation plan"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Consumes placement intent"),
            Dependency("GAP-09 Unified observability", "peer", "Reported actual state for drift detection", required=False)
        ],
        source_of_truth="The versioned intent graph held by this plane; reported actual state is evidence, never authority.",
        assumptions=[
            "Declarations arrive from authenticated principals with a resolvable tenant",
            "Reported actual state may be stale, partial, or absent for disconnected sites",
            "Downstream planes are eventually consistent and may reject a step"
        ],
        boundaries={
            "tenant": "one intent graph namespace per tenant, no cross-tenant edges",
            "environment": "environments are disjoint graph roots with independent promotion",
            "site": "site is a node attribute; a plan may span sites but never merges their state",
            "workload": "workload is the smallest addressable graph node"
        },
        mandatory=[
            "Admit or reject every declaration with a recorded reason",
            "Resolve declaration dependencies into a total order or report the cycle",
            "Produce a dry-run plan before any plan is released for execution",
            "Detect drift between intent and reported actual state",
            "Version every graph mutation with a rollback target"
        ],
        optional=[
            "Speculative planning against hypothetical declarations",
            "Cost annotation of plan steps",
            "Graph query language beyond node/edge lookup"
        ],
        non_goals=[
            "Executing plan steps",
            "Acting as a general-purpose configuration database",
            "Reconciling state the estate does not declare",
            "Replacing GitOps as the change entry point"
        ],
        interfaces={
            "declare": "PK_DECLARATION/1 - submit or retract a declaration",
            "plan": "PK_RECONCILIATION_PLAN/1 - dependency-ordered plan with dry-run results",
            "report": "PK_ACTUAL_STATE/1 - reported actual state ingested for drift detection",
            "graph": "PK_INTENT_GRAPH/1 - read-only node and edge projection"
        },
        threats=[
            "A tenant declaring nodes outside its namespace",
            "A compromised reporter forging actual state to mask drift",
            "Declaration floods exhausting planning capacity",
            "Supply-chain substitution of a referenced artifact between plan and execution",
            "Plan replay against a newer graph version"
        ],
        failure_modes=[
            "Dependency cycle in the declared graph",
            "Actual state absent for a disconnected site",
            "Downstream plane rejects a released plan step",
            "Graph version conflict between concurrent declarations"
        ],
        slos=[
            Slo("plan latency", "p99 plan emission under 2s for graphs up to 10k nodes", "0.5% of plans may exceed"),
            Slo("admission correctness", "zero admitted declarations violating policy", "no budget: any breach is a blocker"),
            Slo("drift detection", "drift surfaced within one reconciliation interval of a report", "1% of reports may lag one interval")
        ],
        signals={
            "intent_graph_nodes": "count of nodes per tenant and environment",
            "declaration_admission": "admitted/rejected counter with reason label",
            "plan_emission_seconds": "histogram of plan emission latency",
            "drift_open": "gauge of nodes currently drifted",
            "graph_version": "monotonic version of the authoritative graph"
        },
    )
