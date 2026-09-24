"""Binding contract for GAP-04 - Disconnected-operation controller.

The disconnected-operation controller is what lets an edge site keep working when the control plane is gone. It grants a bounded autonomy lease, narrows what the site may decide for itself as the partition lengthens, and reconciles honestly on reconnect instead of pretending nothing happened.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-04"
ELEMENT_NAME = "Disconnected-operation controller"


def build() -> Contract:
    """Return the production contract for GAP-04."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own site behaviour during control-plane partition: issue and expire bounded autonomy leases, degrade local decision authority as the partition lengthens, and produce a reconciliation record on reconnect."
        ),
        owns=[
            "Autonomy leases and their expiry",
            "Degradation tiers as a partition lengthens",
            "Local decision authority during partition",
            "The reconnection reconciliation record",
            "Cached policy and its staleness bound"
        ],
        not_owns=[
            "Transport or NAT traversal",
            "State replication semantics",
            "Policy authorship",
            "Node lifecycle",
            "Capability grants"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Supplies the policy cached for offline evaluation"),
            Dependency("PLN-07 Security plane", "upstream", "Issues the grants whose revocation must still propagate"),
            Dependency("GAP-12 WAN resilience and NAT traversal", "upstream", "Reports whether the control plane is reachable"),
            Dependency("GAP-01 Edge Node Supervisor", "downstream", "Takes local policy from this controller during partition"),
            Dependency("GAP-05 State replication/consistency model", "peer", "Reconciles divergent state on reconnect")
        ],
        source_of_truth="The autonomy lease: a site may decide only what an unexpired lease permits, and nothing once it expires.",
        assumptions=[
            "A partition may last from seconds to days",
            "Cached policy goes stale and cannot be refreshed during partition",
            "Revocations issued during the partition were not seen locally"
        ],
        boundaries={
            "tenant": "autonomy is granted per site, never per tenant",
            "environment": "lease durations differ per environment",
            "site": "the site is the unit of partition and of autonomy",
            "workload": "existing workloads keep running; new admissions narrow with the tier"
        },
        mandatory=[
            "Issue autonomy leases with an explicit expiry",
            "Narrow local decision authority as the partition lengthens",
            "Refuse decisions the current tier does not permit",
            "Stop granting anything once the lease expires",
            "Produce a reconciliation record naming every local decision on reconnect"
        ],
        optional=[
            "Pre-emptive lease renewal before an expected partition",
            "Operator-forced tier override",
            "Partial policy refresh over a degraded link"
        ],
        non_goals=[
            "Guaranteeing correctness of decisions made on stale policy",
            "Replacing the control plane",
            "Replicating state",
            "Maintaining connectivity"
        ],
        interfaces={
            "lease": "PK_AUTONOMY_LEASE/1 - grant, renew, and expire a site's autonomy",
            "tier": "PK_DEGRADATION_TIER/1 - what the site may decide right now",
            "reconcile": "PK_RECONCILIATION_RECORD/1 - decisions taken during the partition"
        },
        threats=[
            "A site faking a partition to escape control-plane policy",
            "Lease extension without control-plane contact",
            "Revocation suppression during a deliberate partition",
            "Reconciliation record omitting an inconvenient local decision"
        ],
        failure_modes=[
            "Lease expires while still partitioned",
            "Cached policy older than its staleness bound",
            "Reconnect reveals conflicting decisions",
            "Clock skew makes a lease appear valid when it is not"
        ],
        slos=[
            Slo("lease enforcement", "zero decisions taken under an expired lease", "no budget"),
            Slo("record completeness", "every local decision appears in the reconciliation record", "no budget"),
            Slo("tier correctness", "zero decisions permitted above the current degradation tier", "no budget")
        ],
        signals={
            "autonomy_tier": "current degradation tier for the site",
            "lease_remaining": "gauge of ticks until the autonomy lease expires",
            "offline_decisions": "counter of decisions taken during partition, by kind",
            "reconcile_conflicts": "counter of conflicts surfaced on reconnect",
            "policy_staleness_seconds": "gauge of cached-policy age"
        },
    )
