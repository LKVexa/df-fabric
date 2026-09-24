"""Binding contract for INV-01 - Legacy infrastructure substrate.

The legacy infrastructure substrate is everything that already runs: physical hosts and long-lived VMs, many past vendor support, some with nobody clearly responsible for them. Moving to a new platform starts with an honest inventory. This element compares what the records say with what was actually discovered, tracks end-of-life dates, and refuses to schedule a host for migration until every workload on it has an owner.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-01"
ELEMENT_NAME = "Legacy infrastructure substrate"


def build() -> Contract:
    """Return the production contract for INV-01."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the legacy estate inventory: discovered versus recorded hosts, end-of-life tracking, workload ownership and migration eligibility."
        ),
        owns=[
            "Discovered-host inventory",
            "Reconciliation against the system of record",
            "End-of-life tracking",
            "Workload ownership mapping",
            "Migration eligibility decisions"
        ],
        not_owns=[
            "Performing migrations",
            "Hardware procurement",
            "Workload re-platforming",
            "Network changes",
            "Decommissioning hardware"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies discovered host facts"),
            Dependency("INV-02 Container substrate", "downstream", "Receives workloads that are eligible to move"),
            Dependency("INV-06 Traditional IaC", "downstream", "Codifies hosts once they are inventoried"),
            Dependency("GAP-09 Unified observability", "peer", "Reports where the records and discovery disagree")
        ],
        source_of_truth="Discovery, not the system of record: a host that answers is real, whatever the records say.",
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
            "Reconcile discovered hosts against recorded ones",
            "Flag every host past end of life",
            "Map every workload to an owner",
            "Refuse migration of hosts with unowned workloads",
            "Report ghosts (recorded, not found) and strays (found, not recorded)"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Migrating workloads",
            "Buying hardware",
            "Decommissioning"
        ],
        interfaces={
            "inventory": "PK_LEGACY_INV/1 - discovered hosts and their workloads",
            "reconcile": "PK_LEGACY_RECONCILE/1 - ghosts, strays and matches",
            "eligibility": "PK_LEGACY_ELIGIBLE/1 - migration eligibility with reasons"
        },
        threats=[
            "Unknown host running unpatched software",
            "Migration breaking an unowned dependency",
            "End-of-life hardware left in production"
        ],
        failure_modes=[
            "Host unreachable",
            "Record without host",
            "Host without record",
            "Owner unknown"
        ],
        slos=[
            Slo("inventory accuracy", "every discovered host is either recorded or flagged as a stray", "no budget"),
            Slo("safe migration", "zero hosts with unowned workloads scheduled to move", "no budget"),
            Slo("freshness", "discovery re-run at least daily", "one missed run per week")
        ],
        signals={
            "hosts": "gauge by state",
            "ghosts": "gauge",
            "strays": "gauge",
            "eol_hosts": "gauge"
        },
    )
