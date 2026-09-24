"""Binding contract for INV-30 - Capability hardware sandbox.

The capability hardware sandbox is CHERI-shaped: pointers carry bounds and permissions the hardware itself checks, so a bug cannot be turned into an arbitrary write. It is the one tier where memory safety is enforced below the software stack -- and it exists on very little hardware, which this element states rather than glosses over.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-30"
ELEMENT_NAME = "Capability hardware sandbox"


def build() -> Contract:
    """Return the production contract for INV-30."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own capability-hardware sandboxing: represent memory capabilities with their bounds and permissions, enforce monotonic narrowing on derivation, and refuse any access outside a capability's bounds or permission set."
        ),
        owns=[
            "Capability representation (base, length, permissions, validity)",
            "Monotonic narrowing on derivation",
            "Bounds and permission checking on access",
            "Capability invalidation",
            "Refusal of permission amplification"
        ],
        not_owns=[
            "The CPU implementation",
            "Compiler toolchains",
            "Operating-system policy",
            "Other isolation tiers",
            "Placement"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Reports whether capability hardware exists on this node at all"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads to this tier where hardware allows"),
            Dependency("INV-41 Capability security", "peer", "Shares the attenuation-only model at the software level"),
            Dependency("INV-45 SFI mechanisms", "peer", "Software fallback where the hardware is absent")
        ],
        source_of_truth="The capability itself: bounds and permissions travel with the pointer and cannot be widened by any operation.",
        assumptions=[
            "Capability hardware is rare and most nodes will not have it",
            "A derived capability may only be narrower than its parent",
            "An invalidated capability can never be revalidated"
        ],
        boundaries={
            "tenant": "capabilities never cross a tenant's address space",
            "environment": "an environment may require this tier for some trust classes",
            "site": "most sites will not have the hardware and must report its absence",
            "workload": "a workload's root capability bounds its whole address space"
        },
        mandatory=[
            "Carry bounds and permissions with every capability",
            "Permit derivation only by narrowing",
            "Refuse access outside a capability's bounds",
            "Refuse an operation requiring a permission the capability lacks",
            "Make invalidation permanent"
        ],
        optional=[
            "Sealed capabilities for opaque handles",
            "Compartment identifiers",
            "Capability revocation sweeps"
        ],
        non_goals=[
            "Implementing the CPU",
            "Emulating capability hardware in software",
            "Claiming this tier where the hardware is absent",
            "Replacing software capability security"
        ],
        interfaces={
            "derive": "PK_CAPABILITY/1 - derive a narrower capability from a held one",
            "access": "PK_CAPABILITY_ACCESS/1 - a bounds- and permission-checked access"
        },
        threats=[
            "Pointer forgery producing an out-of-bounds capability",
            "Permission amplification during derivation",
            "Use of an invalidated capability after free",
            "Claiming the tier on hardware that lacks it"
        ],
        failure_modes=[
            "Access outside bounds",
            "Missing permission for the operation",
            "Derivation attempting to widen",
            "Use of an invalidated capability"
        ],
        slos=[
            Slo("bounds", "zero accesses served outside a capability's bounds", "no budget"),
            Slo("monotonicity", "zero derivations widening bounds or permissions", "no budget"),
            Slo("invalidation", "zero uses of an invalidated capability", "no budget")
        ],
        signals={
            "capability_derivations": "counter by narrowing amount",
            "bounds_violations": "counter of refused out-of-bounds accesses",
            "permission_violations": "counter by missing permission",
            "invalidated_uses": "counter of attempts to use a dead capability"
        },
    )
