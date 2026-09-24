"""Binding contract for GAP-10 - Power/thermal-aware scheduling.

Power and thermal-aware scheduling is the constraint a data-centre scheduler never had to model. An edge node in a hot cabinet on a battery cannot run what a racked node can, and this element makes that a hard ceiling the scheduler cannot argue with.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-10"
ELEMENT_NAME = "Power/thermal-aware scheduling"


def build() -> Contract:
    """Return the production contract for GAP-10."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own power and thermal ceilings per node: convert measured thermal and power state into a capacity ceiling and an exclusion verdict, and lower the ceiling before hardware throttling or shutdown does it unpredictably."
        ),
        owns=[
            "Thermal and power state per node",
            "Capacity ceiling derived from that state",
            "Node exclusion under thermal emergency",
            "Hysteresis on ceiling recovery",
            "Battery-budget awareness"
        ],
        not_owns=[
            "Placement decisions",
            "Capacity targets",
            "Hardware fan or governor control",
            "Node lifecycle",
            "Accelerator allocation"
        ],
        dependencies=[
            Dependency("GAP-09 Unified observability", "upstream", "Supplies temperature, power draw and battery signals"),
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports whether thermal sensors exist at all"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Excludes nodes this element marks excluded"),
            Dependency("PLN-05 Elasticity plane", "downstream", "Has its ceiling lowered by this element"),
            Dependency("GAP-11 Accelerator scheduling", "peer", "Accelerators are the dominant thermal load")
        ],
        source_of_truth="The measured thermal and power signals; a node with no sensor data is treated as constrained, not as cool.",
        assumptions=[
            "Sensors may be absent on cheap edge hardware",
            "Thermal response lags load by seconds to minutes",
            "A battery-powered node has a finite energy budget, not just a rate limit"
        ],
        boundaries={
            "tenant": "thermal ceilings are node-level and applied to all tenants equally",
            "environment": "thermal policy differs per environment",
            "site": "a site may share a cooling domain, so ceilings can correlate",
            "workload": "no workload is exempt from a thermal ceiling"
        },
        mandatory=[
            "Derive a capacity ceiling from measured thermal and power state",
            "Treat missing sensor data as constrained rather than cool",
            "Exclude a node entirely under thermal emergency",
            "Apply hysteresis so a node does not oscillate in and out of service",
            "Lower the ceiling before hardware throttling engages"
        ],
        optional=[
            "Battery discharge forecasting",
            "Cooling-domain correlation across a site",
            "Workload-class-aware shedding"
        ],
        non_goals=[
            "Controlling fans or CPU governors",
            "Making placement decisions",
            "Guaranteeing a node never throttles",
            "Exempting any workload from a ceiling"
        ],
        interfaces={
            "thermal": "PK_THERMAL_STATE/1 - measured temperature, power draw and battery state",
            "ceiling": "PK_POWER_CEILING/1 - derived capacity ceiling and exclusion verdict",
            "policy": "PK_THERMAL_POLICY/1 - thresholds and hysteresis per environment"
        },
        threats=[
            "Forged cool readings to keep a node accepting work",
            "Thermal denial-of-service driving a site's nodes to exclusion",
            "Ceiling bypass by a privileged workload",
            "Sensor suppression to hide an overheating node"
        ],
        failure_modes=[
            "Sensor data absent or stale",
            "Temperature above the emergency threshold",
            "Battery below its reserve",
            "Ceiling oscillation near a threshold"
        ],
        slos=[
            Slo("emergency exclusion", "zero placements onto a node above its emergency threshold", "no budget"),
            Slo("pre-emption", "ceiling lowered before hardware throttling in 99% of thermal ramps", "1% may be overtaken by hardware"),
            Slo("stability", "no more than one exclusion flip per node per hysteresis window", "1% may exceed under sensor noise")
        ],
        signals={
            "node_temperature": "gauge per node and sensor",
            "power_ceiling": "gauge of derived capacity ceiling per node",
            "thermal_exclusions": "counter of nodes excluded, by reason",
            "battery_reserve": "gauge of remaining battery budget",
            "sensor_absent": "gauge of nodes with no usable thermal evidence"
        },
    )
