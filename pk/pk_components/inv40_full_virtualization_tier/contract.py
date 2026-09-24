"""Binding contract for INV-40 - Full virtualization tier.

The full virtualization tier is the heavyweight end: a complete machine with its own kernel and a full device model. It is the tier you use when the workload is hostile or the guest OS is not yours, and it costs seconds to boot and hundreds of megabytes to run -- numbers this element states plainly so the tier is chosen on purpose rather than by default.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-40"
ELEMENT_NAME = "Full virtualization tier"


def build() -> Contract:
    """Return the production contract for INV-40."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own full-machine virtualization: run a complete guest with its own kernel and full device model, enforce the strongest available isolation boundary, and account honestly for the boot time and memory footprint the tier costs."
        ),
        owns=[
            "Full guest lifecycle with a complete device model",
            "The strongest-available isolation boundary for a guest",
            "Boot-time and footprint accounting",
            "Guest-OS opacity (no host introspection assumptions)",
            "Refusal to run without the hardware primitive"
        ],
        not_owns=[
            "Guest operating systems",
            "The CPU primitive itself",
            "Placement",
            "Capacity targets",
            "MicroVM device minimalism"
        ],
        dependencies=[
            Dependency("INV-23 Hardware virtualization primitive", "upstream", "Provides the extension this tier requires absolutely"),
            Dependency("PLN-04 Execution plane", "upstream", "Admits hostile-class workloads to this tier"),
            Dependency("INV-32 Elastic virtualization", "downstream", "Adjusts resources for these guests", required=False),
            Dependency("INV-33 Virtualization controller", "peer", "Holds the lease for guests in this tier")
        ],
        source_of_truth="The hardware virtualization primitive; without it this tier does not exist and is never emulated in software.",
        assumptions=[
            "The guest OS is not under our control and may be hostile",
            "Boot takes seconds, not milliseconds",
            "Memory footprint is hundreds of megabytes, not tens"
        ],
        boundaries={
            "tenant": "one guest, one tenant, no sharing of any kind",
            "environment": "an environment may reserve this tier for specific trust classes",
            "site": "a site without the hardware primitive cannot offer this tier",
            "workload": "one full guest per workload"
        },
        mandatory=[
            "Require the hardware virtualization primitive and refuse without it",
            "Account boot time and memory footprint per guest",
            "Make no assumption about guest-OS internals",
            "Enforce one tenant per guest with no shared devices",
            "Never emulate the tier in software when the primitive is absent"
        ],
        optional=[
            "Nested virtualization for the guest",
            "Live migration",
            "GPU passthrough under policy"
        ],
        non_goals=[
            "Minimal device models",
            "Millisecond boots",
            "Introspecting the guest OS",
            "Providing a software fallback when the hardware primitive is missing"
        ],
        interfaces={
            "create": "PK_FULL_VM/1 - create a full guest with its device model and footprint",
            "boot": "PK_FULL_VM_BOOT/1 - boot result with elapsed time and resident footprint"
        },
        threats=[
            "A hostile guest OS attacking the VMM",
            "Software emulation offered as an equivalent when hardware is absent",
            "Device sharing between guests of different tenants",
            "Host introspection assumptions broken by a modified guest"
        ],
        failure_modes=[
            "Hardware primitive unavailable",
            "Guest exceeds its footprint ceiling",
            "Boot exceeds the tier's budget",
            "Guest OS fails to start"
        ],
        slos=[
            Slo("primitive requirement", "zero guests started without the hardware primitive", "no budget"),
            Slo("tenant exclusivity", "zero devices shared between guests of different tenants", "no budget"),
            Slo("footprint honesty", "100% of guests accounted at their real resident size", "no budget")
        ],
        signals={
            "full_vm_instances": "gauge by tenant and state",
            "boot_seconds": "histogram against the tier budget",
            "resident_mib": "gauge of real footprint per guest",
            "primitive_refusals": "counter of starts refused for a missing primitive"
        },
    )
