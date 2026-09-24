"""Binding contract for INV-24 - MicroVM runtime.

The microVM runtime is the Firecracker-shaped tier: a stripped VMM with a minimal device model that boots in milliseconds. Its whole value is that the attack surface is small and the boot is fast, so this element refuses a configuration that widens the one or destroys the other.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-24"
ELEMENT_NAME = "MicroVM runtime"


def build() -> Contract:
    """Return the production contract for INV-24."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own microVM instance lifecycle: boot a guest with only the declared minimal device set, enforce the boot-time budget, and refuse any configuration that adds a device outside the permitted minimal model."
        ),
        owns=[
            "MicroVM instance lifecycle (create, boot, pause, stop)",
            "The permitted minimal device model",
            "Boot-time budget enforcement",
            "Per-instance resource limits",
            "Refusal of out-of-model device requests"
        ],
        not_owns=[
            "The CPU virtualization primitive",
            "Device backend implementations",
            "Snapshot format",
            "Placement",
            "Guest operating systems"
        ],
        dependencies=[
            Dependency("INV-23 Hardware virtualization primitive", "upstream", "Supplies the CPU extension the VMM requires"),
            Dependency("INV-25 MicroVM devices", "upstream", "Supplies the permitted device model"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads to this tier"),
            Dependency("INV-26 MicroVM snapshotting", "peer", "Restores instances this runtime would otherwise cold-boot"),
            Dependency("INV-35 High-performance VM I/O", "peer", "Provides the virtio datapath", required=False)
        ],
        source_of_truth="The declared minimal device model; a device not in it does not exist for this runtime.",
        assumptions=[
            "A cold boot costs tens of milliseconds and a restore far less",
            "Every added device is added attack surface",
            "A guest may fail to boot without the VMM being at fault"
        ],
        boundaries={
            "tenant": "one microVM serves exactly one tenant for its lifetime",
            "environment": "boot budgets and device models differ per environment",
            "site": "a site may run fewer devices than the model permits, never more",
            "workload": "one workload per microVM instance"
        },
        mandatory=[
            "Boot only with devices from the permitted minimal model",
            "Refuse any device request outside that model",
            "Enforce a boot-time budget and report a breach",
            "Apply per-instance memory and vCPU limits at creation",
            "Destroy instance state on stop without reuse across tenants"
        ],
        optional=[
            "Snapshot-backed restore",
            "Balloon-driven memory reclaim",
            "MMDS metadata service"
        ],
        non_goals=[
            "Full device emulation",
            "Live migration",
            "Running an unmodified general-purpose VM image",
            "Adding devices to satisfy a guest that wants them"
        ],
        interfaces={
            "create": "PK_MICROVM/1 - create an instance with its device set and limits",
            "boot": "PK_MICROVM_BOOT/1 - boot result with elapsed time against the budget",
            "lifecycle": "PK_MICROVM_LIFECYCLE/1 - pause, resume, stop"
        },
        threats=[
            "Device-model expansion widening the attack surface",
            "A guest escaping through an emulated device",
            "Boot-budget exhaustion used as a denial-of-service",
            "Instance memory reused across tenants without scrub"
        ],
        failure_modes=[
            "Requested device is outside the model",
            "Boot exceeds its budget",
            "Virtualization primitive unavailable",
            "Guest kernel fails to start"
        ],
        slos=[
            Slo("device model", "zero instances booted with an out-of-model device", "no budget"),
            Slo("boot time", "p99 cold boot under the declared budget", "1% may exceed and are reported"),
            Slo("tenant isolation", "zero instances reused across tenants without destruction", "no budget")
        ],
        signals={
            "microvm_instances": "gauge by state and tenant",
            "boot_seconds": "histogram of boot time against the budget",
            "device_refusals": "counter of out-of-model device requests",
            "boot_budget_breaches": "counter of boots that exceeded the budget"
        },
    )
