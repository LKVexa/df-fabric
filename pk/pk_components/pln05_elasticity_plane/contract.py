"""Binding contract for PLN-05 - Elasticity plane.

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-05"
ELEMENT_NAME = "Elasticity plane"


def build() -> Contract:
    """Return the production contract for PLN-05."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own capacity targets per workload: convert observed demand into a bounded, hysteretic scale decision including scale-to-zero, and never emit a target outside the declared floor and ceiling."
        ),
        owns=[
            "Capacity targets per workload",
            "Scale-up and scale-down hysteresis",
            "Scale-to-zero and cold-start admission",
            "Floor and ceiling enforcement",
            "Oscillation suppression"
        ],
        not_owns=[
            "Placement of new capacity",
            "Node provisioning",
            "Workload isolation",
            "The demand signal itself",
            "Cost accounting"
        ],
        dependencies=[
            Dependency("GAP-09 Unified observability", "upstream", "Supplies the demand signal"),
            Dependency("PLN-01 Intent plane", "upstream", "Supplies declared floor, ceiling, and target utilisation"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Places the capacity this plane asks for"),
            Dependency("GAP-10 Power/thermal-aware scheduling", "peer", "May cap the ceiling below the declared value")
        ],
        source_of_truth="The declared floor/ceiling from the intent plane; observed demand is input, never authority.",
        assumptions=[
            "The demand signal is delayed and noisy",
            "Cold start is expensive enough that scale-to-zero needs an explicit grace period",
            "A ceiling may be lowered externally by power or thermal pressure"
        ],
        boundaries={
            "tenant": "capacity targets and ceilings are per tenant",
            "environment": "hysteresis parameters differ per environment",
            "site": "a site's ceiling may be lower than the environment ceiling",
            "workload": "each workload has an independent controller instance"
        },
        mandatory=[
            "Emit a capacity target within the declared floor and ceiling at all times",
            "Apply separate scale-up and scale-down thresholds",
            "Hold a scale-down decision for the declared grace period before acting",
            "Support scale-to-zero when the floor is zero",
            "Suppress oscillation between adjacent targets"
        ],
        optional=[
            "Predictive pre-scaling",
            "Cost-aware ceiling selection",
            "Burst credit accounting"
        ],
        non_goals=[
            "Placing or provisioning capacity",
            "Deciding node count",
            "Guaranteeing cold-start latency",
            "Overriding an externally lowered ceiling"
        ],
        interfaces={
            "observe": "PK_DEMAND/1 - demand samples per workload",
            "target": "PK_CAPACITY_TARGET/1 - emitted capacity target with the reason",
            "limits": "PK_CAPACITY_LIMITS/1 - declared floor, ceiling, and hysteresis parameters"
        },
        threats=[
            "Forged demand signal driving a tenant's bill or starving a peer",
            "Ceiling bypass through a crafted limits declaration",
            "Oscillation induced deliberately to churn placement",
            "Scale-to-zero used to suppress a security-relevant workload"
        ],
        failure_modes=[
            "Demand signal stops arriving",
            "Ceiling lowered below the current target",
            "Cold start exceeds the grace period",
            "Floor and ceiling declared inconsistently"
        ],
        slos=[
            Slo("target bounds", "zero targets outside the declared floor/ceiling", "no budget"),
            Slo("reaction time", "p95 scale-up decision within two demand samples of threshold breach", "5% may take a third sample"),
            Slo("stability", "no more than one direction change per workload per grace period", "1% of workloads may exceed under demand step changes")
        ],
        signals={
            "capacity_target": "gauge per workload with the emitting reason",
            "scale_decisions": "counter by direction and reason",
            "suppressed_oscillations": "counter of decisions withheld by hysteresis",
            "demand_staleness_seconds": "gauge of age of the newest demand sample"
        },
    )
