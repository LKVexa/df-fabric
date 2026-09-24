"""Binding contract for INV-06 - Traditional IaC.

Traditional infrastructure-as-code works in two steps: plan what will change, then apply that plan against a recorded state. It goes wrong when the world moves between the two -- someone else applies, or the plan is old. So a plan is tied to the state serial it was made against and is refused if that has moved; drift is detected by comparing real resources with the state; and protected resources cannot be destroyed by a plan at all.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-06"
ELEMENT_NAME = "Traditional IaC"


def build() -> Contract:
    """Return the production contract for INV-06."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own plan and apply against recorded state: diffing, state serials, stale-plan refusal, drift detection and destroy protection."
        ),
        owns=[
            "Plan computation",
            "State serials and locking",
            "Stale-plan refusal",
            "Drift detection",
            "Destroy protection"
        ],
        not_owns=[
            "Cloud provider APIs",
            "Configuration language design",
            "Secrets",
            "CI pipelines",
            "GitOps sync"
        ],
        dependencies=[
            Dependency("INV-01 Legacy infrastructure substrate", "upstream", "Supplies inventoried hosts to codify"),
            Dependency("INV-07 GitOps transition layer", "downstream", "Moves IaC changes into a git-driven flow"),
            Dependency("INV-08 Dynamic infrastructure model", "downstream", "Replaces static definitions for elastic pools"),
            Dependency("GAP-13 Policy engine", "peer", "Evaluates plans against policy before apply")
        ],
        source_of_truth="The state file at its current serial; a plan is valid only against the serial it was computed from.",
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
            "Compute a plan before every change",
            "Refuse to apply a plan made against an older serial",
            "Detect drift between real resources and state",
            "Refuse plans that destroy protected resources",
            "Advance the serial on every successful apply"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Calling provider APIs",
            "Designing configuration languages",
            "Running CI"
        ],
        interfaces={
            "plan": "PK_IAC_PLAN/1 - create, update, delete against a serial",
            "apply": "PK_IAC_APPLY/1 - apply a plan to state",
            "drift": "PK_IAC_DRIFT/1 - differences between reality and state"
        },
        threats=[
            "Stale plan overwriting someone else's change",
            "Accidental deletion of a database",
            "Out-of-band change silently reverted"
        ],
        failure_modes=[
            "Stale plan",
            "Protected resource",
            "Drift found",
            "State locked"
        ],
        slos=[
            Slo("no stale applies", "zero plans applied against a moved serial", "no budget"),
            Slo("protection", "zero protected resources destroyed by plan", "no budget"),
            Slo("drift visibility", "drift detected within one scan interval", "no budget")
        ],
        signals={
            "plans": "counter",
            "applies": "counter",
            "stale_refusals": "counter",
            "drifted": "gauge"
        },
    )
