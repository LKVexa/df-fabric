"""Binding contract for INV-25 - MicroVM devices.

MicroVM devices is where the minimal device model is actually defined and defended. Each device is paravirtual, declares the exact guest-visible surface it exposes, and carries a rationale -- because a device without a reason to exist is attack surface with a justification attached after the fact.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-25"
ELEMENT_NAME = "MicroVM devices"


def build() -> Contract:
    """Return the production contract for INV-25."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the paravirtual device catalogue: define every permitted device, its guest-visible surface and its rationale, and refuse to register a device that emulates legacy hardware or exposes host resources directly."
        ),
        owns=[
            "The paravirtual device catalogue and its schema",
            "Guest-visible surface per device",
            "Rationale and review status for each device",
            "Refusal of legacy emulation",
            "Device surface diffing between model versions"
        ],
        not_owns=[
            "Device backend implementations",
            "MicroVM lifecycle",
            "The I/O datapath",
            "Guest drivers",
            "Snapshot serialization"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Supplies the device-permission policy and the review requirement this catalogue enforces"),
            Dependency("INV-24 MicroVM runtime", "downstream", "Boots only devices this catalogue permits"),
            Dependency("INV-35 High-performance VM I/O", "downstream", "Implements the datapath behind these devices"),
            Dependency("INV-26 MicroVM snapshotting", "peer", "Serializes the device state this catalogue defines"),
            Dependency("INV-43 Transient-execution defense", "peer", "Some device surfaces widen speculation risk", required=False)
        ],
        source_of_truth="The device catalogue entry; a device with no catalogue entry cannot be attached.",
        assumptions=[
            "Every guest-visible register is a potential escape path",
            "Legacy device emulation is a large and unnecessary surface",
            "A device's surface changes between versions and must be diffable"
        ],
        boundaries={
            "tenant": "device catalogues are estate-level, not per tenant",
            "environment": "an environment may permit a narrower catalogue subset",
            "site": "sites may lack the backend for a permitted device",
            "workload": "a workload requests device classes, never specific registers"
        },
        mandatory=[
            "Require a rationale and review status for every catalogue entry",
            "Declare the guest-visible surface of each device explicitly",
            "Refuse legacy hardware emulation entries",
            "Refuse devices exposing host resources directly",
            "Report the surface diff when a device version changes"
        ],
        optional=[
            "Per-device fuzzing status",
            "Surface size budgets",
            "Optional device deprecation timers"
        ],
        non_goals=[
            "Implementing device backends",
            "Writing guest drivers",
            "Emulating legacy PCI or ISA hardware",
            "Deciding which devices a workload gets"
        ],
        interfaces={
            "catalogue": "PK_DEVICE_CATALOGUE/1 - permitted devices with surface and rationale",
            "diff": "PK_DEVICE_SURFACE_DIFF/1 - what changed between two device versions"
        },
        threats=[
            "Guest escape through an emulated device register",
            "Catalogue entries added without review",
            "Host resource exposure through a passthrough device",
            "Surface growth going unnoticed between versions"
        ],
        failure_modes=[
            "Device registered without a rationale",
            "Legacy emulation requested",
            "Surface grows without review",
            "Backend missing for a permitted device"
        ],
        slos=[
            Slo("review coverage", "100% of catalogue entries carry a rationale and reviewer", "no budget"),
            Slo("legacy exclusion", "zero legacy-emulation devices in the catalogue", "no budget"),
            Slo("surface visibility", "every version change produces a surface diff", "no budget")
        ],
        signals={
            "catalogue_size": "gauge of permitted devices",
            "surface_registers": "gauge of total guest-visible registers across the catalogue",
            "unreviewed_entries": "gauge of entries missing a reviewer",
            "surface_growth": "counter of version changes that widened the surface"
        },
    )
