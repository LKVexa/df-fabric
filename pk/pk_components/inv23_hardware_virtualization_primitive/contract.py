"""Binding contract for INV-23 - Hardware virtualization primitive.

The hardware virtualization primitive is the floor everything above it stands on: the CPU's own trap-and-emulate machinery. It is either present and usable or it is not, and no amount of software above it can manufacture it, so this element reports it honestly and refuses to pretend nested virtualization is the same thing as bare metal.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-23"
ELEMENT_NAME = "Hardware virtualization primitive"


def build() -> Contract:
    """Return the production contract for INV-23."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own detection and gating of the CPU virtualization extensions: report whether VT-x/AMD-V, EPT/NPT, and nested virtualization are actually usable on this host, and refuse to advertise a primitive that is present in CPUID but disabled or already claimed."
        ),
        owns=[
            "Detection of CPU virtualization extensions",
            "The usable-versus-present distinction",
            "Nested-virtualization depth reporting",
            "Exclusivity of the KVM-equivalent device",
            "Refusal when the primitive is claimed by another hypervisor"
        ],
        not_owns=[
            "The VMM itself",
            "Guest lifecycle",
            "Device emulation",
            "Isolation policy",
            "Scheduling"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Publishes the probe result this element produces"),
            Dependency("INV-24 MicroVM runtime", "downstream", "Cannot start without this primitive"),
            Dependency("INV-40 Full virtualization tier", "downstream", "Builds its tier on this primitive"),
            Dependency("INV-43 Transient-execution defense", "peer", "Mitigations change what the primitive costs")
        ],
        source_of_truth="A successful open of the virtualization device; CPUID alone is a claim, not proof of usability.",
        assumptions=[
            "The extension may be present in CPUID but disabled in firmware",
            "Another hypervisor may already hold the device exclusively",
            "Nested virtualization is slower and may be disabled by policy"
        ],
        boundaries={
            "tenant": "the primitive is host-level and never tenant-scoped",
            "environment": "an environment may forbid nested virtualization",
            "site": "sites differ in firmware settings and nesting support",
            "workload": "workloads never touch the primitive directly"
        },
        mandatory=[
            "Distinguish present-in-CPUID from actually usable",
            "Detect firmware-disabled extensions and report them as unusable",
            "Report nesting depth rather than a boolean",
            "Refuse when another hypervisor holds the device",
            "Never infer the primitive from the absence of an error"
        ],
        optional=[
            "IOMMU presence reporting",
            "Extension feature-bit detail",
            "Performance counter availability"
        ],
        non_goals=[
            "Implementing a VMM",
            "Enabling the extension in firmware",
            "Emulating virtualization in software",
            "Reporting nested as equivalent to bare metal"
        ],
        interfaces={
            "probe": "PK_VIRT_PRIMITIVE/1 - detect and report the virtualization primitive",
            "claim": "PK_VIRT_CLAIM/1 - exclusive claim on the virtualization device"
        },
        threats=[
            "A guest claiming bare-metal isolation while running nested",
            "Device claim races between hypervisors",
            "Firmware downgrade silently removing the extension",
            "CPUID spoofing in a nested guest"
        ],
        failure_modes=[
            "Extension present but firmware-disabled",
            "Device already claimed",
            "Nested depth exceeds what the environment permits",
            "Extension disappears after a firmware update"
        ],
        slos=[
            Slo("report soundness", "zero hosts reporting the primitive usable when the device cannot be opened", "no budget"),
            Slo("nesting honesty", "zero nested hosts reporting depth 0", "no budget"),
            Slo("probe latency", "p99 probe under 50ms", "1% may exceed")
        ],
        signals={
            "virt_primitive": "usable, present-disabled, or absent",
            "nesting_depth": "gauge of how deeply this host is already virtualized",
            "claim_conflicts": "counter of failed exclusive claims",
            "probe_failures": "counter by reason"
        },
    )
