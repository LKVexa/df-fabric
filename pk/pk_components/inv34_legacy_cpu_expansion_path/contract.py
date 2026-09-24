"""Binding contract for INV-34 - Legacy CPU expansion path.

The legacy CPU expansion path is the unglamorous truth of edge estates: hardware from several generations runs side by side, and a workload built for the newest instruction set will fault on the oldest node. This element defines the baseline everything must run on and makes any step above it an explicit, checked requirement.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-34"
ELEMENT_NAME = "Legacy CPU expansion path"


def build() -> Contract:
    """Return the production contract for INV-34."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the CPU baseline and feature-level policy: define the instruction-set baseline every workload must run on, gate any workload requiring features above it to nodes that actually have them, and never present a higher level to a guest than the host provides."
        ),
        owns=[
            "The instruction-set baseline for the estate",
            "Feature-level definitions above the baseline",
            "Workload-to-node feature matching",
            "The guest-visible feature mask",
            "Refusal to expose a feature the host lacks"
        ],
        not_owns=[
            "CPU procurement",
            "Compiler flags",
            "Placement decisions",
            "Microcode updates",
            "Performance tuning"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports each node's actual CPU features"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Filters candidates on the feature requirement"),
            Dependency("GAP-15 Runtime compatibility certification", "downstream", "Certifies artifact/feature-level pairs"),
            Dependency("INV-43 Transient-execution defense", "peer", "Mitigations may mask features that are physically present")
        ],
        source_of_truth="The node's reported feature set intersected with the estate baseline; a masked feature is absent for every purpose.",
        assumptions=[
            "Nodes span several CPU generations and will for years",
            "A workload compiled for a higher level faults rather than degrades",
            "Mitigations can remove a feature that hardware still advertises"
        ],
        boundaries={
            "tenant": "feature levels are estate policy, not tenant choice",
            "environment": "an environment may raise its baseline above the estate's",
            "site": "a site's oldest node sets its effective ceiling",
            "workload": "a workload declares the level it needs, not the CPU it wants"
        },
        mandatory=[
            "Define an explicit instruction-set baseline",
            "Express a workload's requirement as a feature level, not a CPU model",
            "Refuse to place a workload on a node below its required level",
            "Mask guest-visible features to what the host actually provides",
            "Treat a mitigation-masked feature as absent"
        ],
        optional=[
            "Per-generation performance hints",
            "Automatic recompilation at a lower level",
            "Feature-level migration planning"
        ],
        non_goals=[
            "Emulating missing instructions",
            "Choosing hardware",
            "Presenting a feature the host lacks",
            "Assuming a homogeneous fleet"
        ],
        interfaces={
            "baseline": "PK_CPU_BASELINE/1 - the estate baseline and the levels above it",
            "match": "PK_CPU_MATCH/1 - whether a node satisfies a workload's level",
            "mask": "PK_CPU_MASK/1 - the guest-visible feature set for an instance"
        },
        threats=[
            "A guest seeing a feature the host cannot actually provide",
            "A workload placed below its level faulting in production",
            "Feature-level inflation excluding most of the fleet",
            "A mitigation silently removing a feature a running guest depends on"
        ],
        failure_modes=[
            "No node meets the workload's feature level",
            "Host masks a feature a guest already negotiated",
            "Node reports features it cannot sustain under mitigation",
            "Workload declares a CPU model rather than a level"
        ],
        slos=[
            Slo("placement soundness", "zero workloads placed on a node below their feature level", "no budget"),
            Slo("mask honesty", "zero guests shown a feature the host does not provide", "no budget"),
            Slo("baseline coverage", "100% of the fleet meets the estate baseline", "no budget")
        ],
        signals={
            "feature_level": "gauge of nodes at each level",
            "level_refusals": "counter of placements refused by feature level",
            "masked_features": "counter of features hidden from guests by mitigation",
            "below_baseline_nodes": "gauge of nodes failing the estate baseline"
        },
    )
