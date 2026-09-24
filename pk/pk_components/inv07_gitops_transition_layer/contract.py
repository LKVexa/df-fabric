"""Binding contract for INV-07 - GitOps transition layer.

The GitOps transition layer makes a git repository the source of desired state: a controller applies whatever the approved branch says, reverts changes made behind its back, and reports them. It only follows commits signed by an allowed key, and rolling back means reverting a commit -- so every change to the estate has an author, a review and an undo.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-07"
ELEMENT_NAME = "GitOps transition layer"


def build() -> Contract:
    """Return the production contract for INV-07."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own git-driven reconciliation: signed-commit verification, sync to the cluster, revert and report of out-of-band changes, and rollback by revert."
        ),
        owns=[
            "Signed-commit verification",
            "Sync from commit to live state",
            "Out-of-band change detection and revert",
            "Rollback by revert",
            "Sync history"
        ],
        not_owns=[
            "Git hosting",
            "Code review tooling",
            "The live control store",
            "Image building",
            "Secrets storage"
        ],
        dependencies=[
            Dependency("INV-06 Traditional IaC", "upstream", "The prior change mechanism being replaced"),
            Dependency("INV-05 Current control-state system", "downstream", "The live state this layer corrects"),
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies commit signatures"),
            Dependency("INV-63 Wasm deployment manager", "peer", "The same reconciliation idea for Wasm workloads")
        ],
        source_of_truth="The head commit of the approved branch, if signed by an allowed key; the cluster is corrected toward it.",
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
            "Sync only commits signed by allowed keys",
            "Apply the commit's desired state exactly",
            "Revert and report out-of-band changes",
            "Roll back by reverting a commit",
            "Record which commit each sync applied"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Hosting git",
            "Running code review",
            "Building images"
        ],
        interfaces={
            "sync": "PK_GITOPS_SYNC/1 - commit to live state",
            "drift": "PK_GITOPS_DRIFT/1 - out-of-band changes found",
            "verify": "PK_GITOPS_VERIFY/1 - commit signature check"
        },
        threats=[
            "Unsigned commit deploying unreviewed changes",
            "Manual hotfix silently persisting",
            "Rollback that is not recorded"
        ],
        failure_modes=[
            "Signature invalid",
            "Sync failed",
            "Drift reverted",
            "Branch unavailable"
        ],
        slos=[
            Slo("provenance", "zero unsigned commits applied", "no budget"),
            Slo("convergence", "live state matches head within one sync interval", "1% may exceed"),
            Slo("drift reporting", "every reverted change reported", "no budget")
        ],
        signals={
            "syncs": "counter by outcome",
            "unsigned_refusals": "counter",
            "drift_reverts": "counter"
        },
    )
