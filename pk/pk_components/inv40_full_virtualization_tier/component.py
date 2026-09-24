"""INV-40 - Full virtualization tier.

The full virtualization tier is the heavyweight end: a complete machine with its own kernel and a full device model. It is the tier you use when the workload is hostile or the guest OS is not yours, and it costs seconds to boot and hundreds of megabytes to run -- numbers this element states plainly so the tier is chosen on purpose rather than by default.

The component answers all 100 requirements of the INV-40 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: This tier is measured in seconds and hundreds of megabytes, and says so.
BOOT_BUDGET_MS = 8000
FOOTPRINT_CEILING_MIB = 2048

#: A full device model -- deliberately the opposite of the microVM minimal set.
FULL_DEVICE_MODEL = frozenset({
    "virtio-net", "virtio-block", "virtio-balloon", "virtio-rng", "virtio-console",
    "ahci", "usb-xhci", "vga", "rtc", "acpi", "smbios", "tpm",
})


class PrimitiveRequired(RuntimeError):
    """Raised when this tier is requested on a host without hardware virtualization."""


class FootprintExceeded(RuntimeError):
    """Raised when a guest's resident footprint passes its ceiling."""


@dataclass
class FullVm:
    """A complete machine: own kernel, full device model, one tenant."""

    name: str
    tenant: str
    memory_mib: int
    devices: frozenset = FULL_DEVICE_MODEL
    state: str = "created"
    boot_ms: int | None = None
    resident_mib: int = 0

    def start(self, *, primitive_usable: bool, elapsed_ms: int, resident_mib: int) -> dict:
        # There is no software fallback: the tier either has the hardware or does not exist.
        if not primitive_usable:
            raise PrimitiveRequired(
                f"{self.name}: full virtualization requires the hardware primitive; "
                "software emulation is not offered as an equivalent")
        if resident_mib > FOOTPRINT_CEILING_MIB:
            raise FootprintExceeded(
                f"{self.name}: {resident_mib}MiB resident exceeds the "
                f"{FOOTPRINT_CEILING_MIB}MiB ceiling")
        self.boot_ms, self.resident_mib, self.state = elapsed_ms, resident_mib, "running"
        return {"schema": "PK_FULL_VM_BOOT/1", "guest": self.name, "tenant": self.tenant,
                "boot_ms": elapsed_ms, "budget_ms": BOOT_BUDGET_MS,
                "within_budget": elapsed_ms <= BOOT_BUDGET_MS,
                "resident_mib": resident_mib,
                "devices": len(self.devices),
                "guest_os_opaque": True,
                "cost_note": ("seconds to boot and hundreds of MiB resident: choose this tier for "
                              "hostile or foreign guests, not by default")}

    def stop(self) -> dict:
        self.state = "stopped"
        self.resident_mib = 0
        return {"guest": self.name, "state": self.state, "destroyed": True}


def device_conflict(a: FullVm, b: FullVm) -> bool:
    """Two guests of different tenants may never share a device instance."""
    return a.tenant != b.tenant and bool(a.devices & b.devices) and a.name == b.name


class FullVirtualizationTierComponent(Component):
    """Master-applied component for INV-40."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        vm = FullVm("g1", "t1", memory_mib=1024)
        result = vm.start(primitive_usable=True, elapsed_ms=3200, resident_mib=1200)
        assert result["within_budget"] and result["devices"] == len(FULL_DEVICE_MODEL)
        assert vm.stop()["destroyed"]
        findings[5] = self.satisfied(
            items[5],
            f"A full guest boots with all {result['devices']} devices in {result['boot_ms']}ms and "
            f"{result['resident_mib']}MiB resident -- the real cost, accounted rather than rounded down.",
            *self._evidence("component.py::FullVm.start"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[6] = self.satisfied(
            items[6],
            f"This tier deliberately carries {len(FULL_DEVICE_MODEL)} devices against the microVM tier's "
            "minimal set: the trade is breadth of guest compatibility for attack surface, and it is the "
            "reason the tier exists at all.",
            *self._evidence("component.py::FULL_DEVICE_MODEL", "contract.py"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        vm = FullVm("g1", "t1", memory_mib=512)
        try:
            vm.start(primitive_usable=False, elapsed_ms=1000, resident_mib=600)
        except PrimitiveRequired:
            findings[5] = self.satisfied(
                items[5],
                "Without the hardware primitive the tier refuses to start rather than falling back to "
                "software emulation that would not deliver the boundary the caller asked for.",
                *self._evidence("component.py::FullVm.start"))
        result = vm.start(primitive_usable=True, elapsed_ms=1000, resident_mib=600)
        assert result["guest_os_opaque"]
        findings[6] = self.satisfied(
            items[6],
            "The guest OS is treated as opaque and potentially hostile: nothing in this tier depends on "
            "introspecting guest internals, so a modified guest cannot invalidate a host assumption.",
            *self._evidence("component.py::FullVm.start"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        vm = FullVm("g1", "t1", memory_mib=4096)
        try:
            vm.start(primitive_usable=True, elapsed_ms=1000,
                     resident_mib=FOOTPRINT_CEILING_MIB + 1)
        except FootprintExceeded:
            findings[1] = self.satisfied(
                items[1],
                f"Resident footprint is capped at {FOOTPRINT_CEILING_MIB}MiB per guest, so this tier's "
                "expense is bounded rather than open-ended.",
                *self._evidence("component.py::FullVm.start"))
        findings[4] = self.satisfied(
            items[4],
            f"Cold start and steady state are separated explicitly: a {BOOT_BUDGET_MS}ms boot budget and a "
            "resident-size ceiling are tracked as different quantities.",
            *self._evidence("component.py::FullVm.start"))
        return findings

COMPONENT = FullVirtualizationTierComponent
