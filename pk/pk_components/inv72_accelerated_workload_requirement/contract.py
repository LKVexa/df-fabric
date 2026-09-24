"""Binding contract for INV-72 - Accelerated workload requirement.

An accelerated workload requirement is how a job says what hardware it actually needs: which accelerator class, how much device memory, how many devices, and whether they must share a fast interconnect. Matching is strict on what matters -- a job needing 80 GB is never placed on a 40 GB part -- and device sharing is allowed only when the tenant's isolation class permits partitioning.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-72"
ELEMENT_NAME = "Accelerated workload requirement"


def build() -> Contract:
    """Return the production contract for INV-72."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own accelerator requirements: the requirement schema, strict matching against devices, interconnect constraints, and partition-sharing rules by isolation class."
        ),
        owns=[
            "The accelerator requirement schema",
            "Strict device matching",
            "Interconnect constraints",
            "Partitioned sharing rules",
            "Explained non-matches"
        ],
        not_owns=[
            "Device discovery",
            "Scheduling queues",
            "Driver management",
            "Model code",
            "Power policy"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports the devices available"),
            Dependency("GAP-11 Accelerator scheduling", "downstream", "Schedules requirements this element validates"),
            Dependency("INV-68 Resource packing", "peer", "Packs the non-accelerator dimensions"),
            Dependency("INV-69 Agentic workload layer", "downstream", "Requests accelerators for model tools")
        ],
        source_of_truth="The discovered device inventory; a node's advertised label is not trusted without discovery.",
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
            "Match accelerator class exactly",
            "Require at least the requested device memory",
            "Honour interconnect requirements for multi-device jobs",
            "Share partitioned devices only when isolation allows",
            "Explain every non-match"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Discovering devices",
            "Queueing jobs",
            "Managing drivers"
        ],
        interfaces={
            "requirement": "PK_ACCEL_REQ/1 - class, memory, count, interconnect, isolation",
            "match": "PK_ACCEL_MATCH/1 - selected devices or explained refusal",
            "partition": "PK_ACCEL_PARTITION/1 - a shareable device slice"
        },
        threats=[
            "Job placed on too-small device and failing mid-run",
            "Tenant sharing a device slice with an untrusted tenant",
            "Multi-device job split across slow links"
        ],
        failure_modes=[
            "No matching class",
            "Insufficient memory",
            "Interconnect unavailable",
            "Sharing not permitted"
        ],
        slos=[
            Slo("strict fit", "zero jobs placed below their memory requirement", "no budget"),
            Slo("isolation", "zero partition shares across disallowed isolation classes", "no budget"),
            Slo("match time", "p99 under 10ms", "1% may exceed")
        ],
        signals={
            "matched": "counter by class",
            "refused": "counter by reason",
            "partitions_shared": "gauge"
        },
    )
