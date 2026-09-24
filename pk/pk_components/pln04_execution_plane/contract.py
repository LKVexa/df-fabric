"""Binding contract for PLN-04 - Execution plane.

The execution plane admits a workload to a concrete isolation tier - Wasm component, microVM, unikernel, or full VM - and enforces that the tier actually delivers the isolation the workload's trust class requires. Placement chooses the node; this plane chooses and enforces the boundary.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-04"
ELEMENT_NAME = "Execution plane"


def build() -> Contract:
    """Return the production contract for PLN-04."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the isolation tiers available on a node, admit each workload to the weakest tier that still satisfies its trust class, and refuse admission when no available tier meets it."
        ),
        owns=[
            "The catalogue of isolation tiers on a node",
            "Trust-class to tier admission rules",
            "Tier capability attestation before admission",
            "Workload lifecycle within a tier",
            "Refusal of workloads no tier can isolate"
        ],
        not_owns=[
            "Which node a workload lands on",
            "Runtime internals of any tier",
            "Application composition",
            "Network policy",
            "Hardware capability discovery"
        ],
        dependencies=[
            Dependency("SCH-01 Workload classification and placement", "upstream", "Supplies the workload's trust class and placement"),
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies the node's actual isolation primitives"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Hosted alongside the workload inside the tier"),
            Dependency("GAP-09 Unified observability", "downstream", "Receives admission and lifecycle events"),
            Dependency("PLN-07 Security plane", "peer", "Defines the trust classes this plane admits against")
        ],
        source_of_truth="The node's attested tier catalogue; a tier that cannot be attested is treated as absent.",
        assumptions=[
            "Hardware isolation primitives differ per node and may be absent entirely",
            "A weaker tier is cheaper to start and should be preferred when it suffices",
            "Attestation may fail transiently without the tier being compromised"
        ],
        boundaries={
            "tenant": "no tier is shared between tenants at the same trust class",
            "environment": "tier catalogues are per environment and may be narrowed, never widened, at a site",
            "site": "a site may offer fewer tiers than the environment declares",
            "workload": "one workload occupies exactly one tier instance for its lifetime"
        },
        mandatory=[
            "Maintain an attested catalogue of available isolation tiers",
            "Admit each workload to the weakest sufficient tier for its trust class",
            "Refuse admission when no available tier satisfies the trust class",
            "Treat an unattestable tier as unavailable",
            "Tear the tier down on workload exit without reuse across tenants"
        ],
        optional=[
            "Snapshot-based cold-start acceleration",
            "Tier pre-warming",
            "Per-tier resource overcommit"
        ],
        non_goals=[
            "Placement or scheduling",
            "Implementing the tiers themselves",
            "Admitting an untrusted workload to a process sandbox",
            "Cross-tenant tier reuse"
        ],
        interfaces={
            "admit": "PK_ADMISSION/1 - request admission for a workload at a trust class",
            "catalogue": "PK_TIER_CATALOGUE/1 - attested tiers available on this node",
            "lifecycle": "PK_TIER_LIFECYCLE/1 - start, stop, and teardown events"
        },
        threats=[
            "A workload declaring a lower trust class than it warrants",
            "A forged attestation presenting an absent tier as available",
            "Tier reuse leaking state between tenants",
            "Transient-execution side channels between co-resident tiers",
            "Escape from a process sandbox admitted in place of a microVM"
        ],
        failure_modes=[
            "No available tier satisfies the trust class",
            "Attestation fails for the selected tier",
            "Tier fails to start within its budget",
            "Teardown does not complete, leaving a tier instance orphaned"
        ],
        slos=[
            Slo("admission latency", "p99 admission decision under 50ms", "1% may exceed"),
            Slo("isolation correctness", "zero workloads admitted below their required tier", "no budget"),
            Slo("teardown", "99.99% of tier instances fully torn down before reuse of their resources", "0.01% escalate to node drain")
        ],
        signals={
            "tier_admissions": "counter by tier, trust class, and outcome",
            "tier_refusals": "counter of workloads no tier could isolate",
            "attestation_failures": "counter by tier",
            "tier_instances": "gauge of live instances per tier and tenant",
            "admission_seconds": "histogram of admission decision latency"
        },
    )
