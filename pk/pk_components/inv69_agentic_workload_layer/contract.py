"""Binding contract for INV-69 - Agentic workload layer.

The agentic workload layer runs model-driven agents that plan and call tools. What makes that safe to operate is containment at the plan level: each agent has an allowlist of tools, a step budget, and any tool with side effects waits for a recorded approval before it runs. Every step lands in a transcript, so what an agent did is always reconstructable.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-69"
ELEMENT_NAME = "Agentic workload layer"


def build() -> Contract:
    """Return the production contract for INV-69."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own agent execution governance: tool allowlists, step budgets, approval gates on side-effectful tools, sandbox routing and a complete step transcript."
        ),
        owns=[
            "Per-agent tool allowlists",
            "Step and cost budgets",
            "Approval gates for side-effectful tools",
            "Routing tool execution to a sandbox tier",
            "The step transcript"
        ],
        not_owns=[
            "The model itself",
            "Tool implementations",
            "Sandbox internals",
            "Identity issuance",
            "Business approval workflows"
        ],
        dependencies=[
            Dependency("INV-57 Durable execution", "upstream", "Makes long agent plans survive crashes"),
            Dependency("INV-59 Application authorization", "upstream", "Authorizes the agent's identity for each tool"),
            Dependency("INV-70 Fast agent sandbox", "downstream", "Runs low-risk tool code"),
            Dependency("INV-71 Heavy agent sandbox", "downstream", "Runs high-risk tool code")
        ],
        source_of_truth="The transcript; an agent's own account of what it did is not evidence, the recorded steps are.",
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
            "Refuse tools outside the agent's allowlist",
            "Stop at the step budget",
            "Hold side-effectful tools for approval",
            "Route each tool to the sandbox tier its risk requires",
            "Record every step, refusal and approval"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Running the model",
            "Implementing tools",
            "Building sandboxes"
        ],
        interfaces={
            "step": "PK_AGENT_STEP/1 - one tool call and its outcome",
            "approval": "PK_AGENT_APPROVAL/1 - a recorded human or policy approval",
            "transcript": "PK_AGENT_TRANSCRIPT/1 - ordered steps"
        },
        threats=[
            "Prompt-injected agent calling a destructive tool",
            "Runaway loop consuming budget",
            "Unapproved side effect",
            "Missing record of what an agent did"
        ],
        failure_modes=[
            "Tool not allowed",
            "Budget exhausted",
            "Approval pending",
            "Sandbox unavailable"
        ],
        slos=[
            Slo("containment", "zero calls to tools outside the allowlist", "no budget"),
            Slo("approval", "zero side-effectful calls without an approval record", "no budget"),
            Slo("transcript completeness", "every step recorded", "no budget")
        ],
        signals={
            "steps": "counter by agent",
            "refusals": "counter by reason",
            "approvals": "counter",
            "budget_stops": "counter"
        },
    )
