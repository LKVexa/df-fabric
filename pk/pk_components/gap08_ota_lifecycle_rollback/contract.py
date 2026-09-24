"""Binding contract for GAP-08 - OTA lifecycle/rollback.

OTA lifecycle and rollback is how an edge estate survives its own updates. Every rollout is staged, every stage has a health gate, and the rollback target is pinned before the first node is touched -- so a bad update stops at the canary instead of reaching the fleet.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-08"
ELEMENT_NAME = "OTA lifecycle/rollback"


def build() -> Contract:
    """Return the production contract for GAP-08."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the over-the-air update lifecycle: stage a signed bundle across waves, gate each wave on health, and roll back to the pinned previous version the moment a gate fails."
        ),
        owns=[
            "Rollout waves and their ordering",
            "Per-wave health gates",
            "The pinned rollback target",
            "Automatic rollback on gate failure",
            "Update bundle admission (signed only)"
        ],
        not_owns=[
            "Building update bundles",
            "Signing keys",
            "Node health measurement",
            "Node lifecycle transitions",
            "What the update contains"
        ],
        dependencies=[
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies the update bundle before any wave starts"),
            Dependency("GAP-09 Unified observability", "upstream", "Supplies the health signals each wave gate evaluates"),
            Dependency("GAP-01 Edge Node Supervisor", "downstream", "Drains and restarts nodes as waves proceed"),
            Dependency("GAP-15 Runtime compatibility certification", "upstream", "Certifies the bundle is compatible before rollout")
        ],
        source_of_truth="The pinned rollback target, recorded before the first wave; it is never recomputed mid-rollout.",
        assumptions=[
            "A node may be offline when its wave runs and must be caught later",
            "Health evidence lags the change that caused it",
            "A rollback may itself fail on some nodes"
        ],
        boundaries={
            "tenant": "OTA is estate infrastructure and is never tenant-triggered",
            "environment": "an environment is rolled out independently and does not auto-promote",
            "site": "waves are ordered so no site loses all nodes at once",
            "workload": "workloads are drained per node by the supervisor, not by this element"
        },
        mandatory=[
            "Admit only bundles that pass signature verification",
            "Pin the rollback target before the first node is touched",
            "Evaluate a health gate after every wave",
            "Roll back automatically when a gate fails",
            "Never start a wave while the previous one is unhealthy"
        ],
        optional=[
            "Time-of-day rollout windows",
            "Bandwidth-aware bundle distribution",
            "Manual gate approval for the final wave"
        ],
        non_goals=[
            "Building or signing bundles",
            "Measuring node health",
            "Guaranteeing a rollback succeeds on a bricked node",
            "Promoting between environments"
        ],
        interfaces={
            "rollout": "PK_ROLLOUT/1 - start a staged rollout of a verified bundle",
            "gate": "PK_ROLLOUT_GATE/1 - the health verdict for one wave",
            "rollback": "PK_ROLLBACK/1 - revert to the pinned target"
        },
        threats=[
            "An unsigned bundle entering through a manual path",
            "Gate suppression to push a bad update through",
            "Rollback target repointed mid-rollout",
            "Wave ordering manipulated to take out a whole site"
        ],
        failure_modes=[
            "Health gate fails after a wave",
            "A node is offline during its wave",
            "Rollback fails on a subset of nodes",
            "Bundle fails signature verification"
        ],
        slos=[
            Slo("blast radius", "a failing update reaches no more than the first wave before rollback", "no budget"),
            Slo("rollback pinning", "zero rollouts started without a pinned rollback target", "no budget"),
            Slo("gate honesty", "zero waves started while the previous gate was failing", "no budget")
        ],
        signals={
            "rollout_wave": "current wave index and its state",
            "gate_verdicts": "counter by wave and outcome",
            "rollbacks": "counter with the wave that triggered them",
            "nodes_updated": "gauge by version",
            "deferred_nodes": "gauge of nodes offline during their wave"
        },
    )
