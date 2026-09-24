"""Binding contract for INV-32 - Elastic virtualization.

Elastic virtualization is memory and vCPU that move while the guest is running -- ballooning, hot-plug, free-page reporting. It is how an edge node runs more than it has, and it is also how a node gets OOM-killed, so every adjustment here is bounded and reversible.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-32"
ELEMENT_NAME = "Elastic virtualization"


def build() -> Contract:
    """Return the production contract for INV-32."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own live resource adjustment for running guests: grow and shrink guest memory and vCPUs within declared floors and ceilings, never reclaim below a guest's working-set floor, and refuse an adjustment that would oversubscribe the host past its reserve."
        ),
        owns=[
            "Live memory reclaim and growth per guest",
            "vCPU hot-plug within declared bounds",
            "The host reserve that is never allocated",
            "Guest working-set floors",
            "Refusal of oversubscription past the reserve"
        ],
        not_owns=[
            "Capacity targets",
            "Placement",
            "Guest applications",
            "The hypervisor's allocator",
            "Thermal ceilings"
        ],
        dependencies=[
            Dependency("INV-33 Virtualization controller", "upstream", "Issues the adjustment requests this element applies"),
            Dependency("PLN-05 Elasticity plane", "upstream", "Supplies the capacity target driving adjustment"),
            Dependency("GAP-10 Power/thermal-aware scheduling", "upstream", "May lower the host ceiling"),
            Dependency("INV-24 MicroVM runtime", "downstream", "Hosts the guests being adjusted")
        ],
        source_of_truth="The host's declared reserve and each guest's working-set floor; neither may be crossed to satisfy a target.",
        assumptions=[
            "A guest reclaimed below its working set will thrash or be OOM-killed",
            "The host needs headroom for its own operation",
            "Ballooning is cooperative and a guest may refuse or stall"
        ],
        boundaries={
            "tenant": "one tenant's growth may not push another below its floor",
            "environment": "reserve fractions differ per environment",
            "site": "a site's total memory is the hard bound",
            "workload": "each guest carries its own floor and ceiling"
        },
        mandatory=[
            "Never allocate into the host reserve",
            "Never reclaim a guest below its working-set floor",
            "Bound every adjustment by the guest's declared floor and ceiling",
            "Report an adjustment the guest did not honour",
            "Make every adjustment reversible"
        ],
        optional=[
            "Free-page reporting",
            "Memory hot-unplug",
            "Predictive reclaim"
        ],
        non_goals=[
            "Deciding capacity targets",
            "Placing guests",
            "Guaranteeing a guest cooperates",
            "Overcommitting past the host reserve"
        ],
        interfaces={
            "adjust": "PK_RESOURCE_ADJUSTMENT/1 - request a memory or vCPU change for a guest",
            "host": "PK_HOST_RESOURCES/1 - total, reserved, allocated and free"
        },
        threats=[
            "Oversubscription driving the host into OOM",
            "A guest inflating its floor to avoid reclaim",
            "Reclaim used to starve a rival tenant",
            "Balloon driver compromise reporting false free pages"
        ],
        failure_modes=[
            "Adjustment would cross the host reserve",
            "Adjustment would push a guest below its floor",
            "Guest does not honour a reclaim request",
            "Requested vCPU count outside the guest's bounds"
        ],
        slos=[
            Slo("reserve", "zero allocations into the host reserve", "no budget"),
            Slo("floors", "zero guests reclaimed below their working-set floor", "no budget"),
            Slo("reversibility", "100% of applied adjustments reversible to the previous value", "no budget")
        ],
        signals={
            "guest_memory_mib": "gauge per guest with its floor and ceiling",
            "host_free_mib": "gauge of allocatable memory outside the reserve",
            "adjustments": "counter by direction and outcome",
            "unhonoured_reclaims": "counter of guests that did not return memory",
            "reserve_refusals": "counter of adjustments refused at the reserve"
        },
    )
