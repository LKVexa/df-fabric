"""INV-25 - MicroVM devices.

MicroVM devices is where the minimal device model is actually defined and defended. Each device is paravirtual, declares the exact guest-visible surface it exposes, and carries a rationale -- because a device without a reason to exist is attack surface with a justification attached after the fact.

The component answers all 100 requirements of the INV-25 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Device classes that are never permitted, whatever rationale is offered.
FORBIDDEN_CLASSES = frozenset({"legacy-emulation", "host-passthrough", "raw-mmio"})


class DeviceRejected(PermissionError):
    """Raised when a device may not enter the catalogue."""


@dataclass(frozen=True)
class DeviceSpec:
    """One paravirtual device: what the guest can see, and why it exists at all."""

    name: str
    device_class: str              # "paravirtual" | "legacy-emulation" | "host-passthrough" | ...
    version: str
    registers: frozenset           # guest-visible register names
    rationale: str = ""
    reviewer: str = ""

    @property
    def surface(self) -> int:
        return len(self.registers)


@dataclass
class DeviceCatalogue:
    """The closed set of devices a microVM may attach."""

    environment: str
    devices: dict = field(default_factory=dict)   # name -> DeviceSpec

    def register(self, spec: DeviceSpec) -> DeviceSpec:
        if spec.device_class in FORBIDDEN_CLASSES:
            raise DeviceRejected(
                f"{spec.name}: device class {spec.device_class!r} is never permitted")
        if not spec.rationale.strip() or not spec.reviewer.strip():
            raise DeviceRejected(
                f"{spec.name}: a catalogue entry requires both a rationale and a reviewer")
        self.devices[spec.name] = spec
        return spec

    def permitted(self) -> set:
        return set(self.devices)

    def total_surface(self) -> int:
        return sum(d.surface for d in self.devices.values())

    def diff(self, old: DeviceSpec, new: DeviceSpec) -> dict:
        """Report exactly what a version bump did to the guest-visible surface."""
        if old.name != new.name:
            raise ValueError("cannot diff two different devices")
        added = sorted(new.registers - old.registers)
        removed = sorted(old.registers - new.registers)
        return {"schema": "PK_DEVICE_SURFACE_DIFF/1", "device": new.name,
                "from": old.version, "to": new.version,
                "added": added, "removed": removed,
                "widened": bool(added),
                "surface": {"before": old.surface, "after": new.surface}}


class MicrovmDevicesComponent(Component):
    """Master-applied component for INV-25."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        cat = DeviceCatalogue("prod")
        cat.register(DeviceSpec("virtio-net", "paravirtual", "1.0",
                                frozenset({"queue_sel", "queue_size", "status"}),
                                rationale="guest networking", reviewer="sec-team"))
        cat.register(DeviceSpec("virtio-block", "paravirtual", "1.0",
                                frozenset({"capacity", "status"}),
                                rationale="root filesystem", reviewer="sec-team"))
        assert cat.permitted() == {"virtio-net", "virtio-block"} and cat.total_surface() == 5
        findings[5] = self.satisfied(
            items[5],
            f"The catalogue is closed and measurable: {len(cat.permitted())} devices exposing "
            f"{cat.total_surface()} guest-visible registers in total.",
            *self._evidence("component.py::DeviceCatalogue"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        cat = DeviceCatalogue("prod")
        proven = []
        for cls in ("legacy-emulation", "host-passthrough"):
            try:
                cat.register(DeviceSpec("x", cls, "1.0", frozenset(),
                                        rationale="needed", reviewer="someone"))
            except DeviceRejected:
                proven.append(cls)
        assert len(proven) == 2
        findings[2] = self.satisfied(
            items[2],
            f"Legacy emulation and host passthrough are refused outright ({', '.join(proven)}), so no "
            "rationale can talk a direct host-resource exposure into the model.",
            *self._evidence("component.py::FORBIDDEN_CLASSES"))
        try:
            cat.register(DeviceSpec("virtio-gpu", "paravirtual", "1.0", frozenset({"fb"})))
        except DeviceRejected:
            findings[7] = self.satisfied(
                items[7],
                "A device without a rationale and a named reviewer cannot enter the catalogue, so surface "
                "is never added anonymously.",
                *self._evidence("component.py::DeviceCatalogue.register"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        cat = DeviceCatalogue("prod")
        v1 = DeviceSpec("virtio-net", "paravirtual", "1.0", frozenset({"a", "b"}),
                        rationale="networking", reviewer="sec")
        v2 = DeviceSpec("virtio-net", "paravirtual", "1.1", frozenset({"a", "b", "c"}),
                        rationale="networking", reviewer="sec")
        diff = cat.diff(v1, v2)
        assert diff["widened"] and diff["added"] == ["c"]
        findings[6] = self.satisfied(
            items[6],
            "A version bump produces an explicit surface diff (1.0 -> 1.1 added register 'c'), so surface "
            "growth is a reported event rather than something noticed later.",
            *self._evidence("component.py::DeviceCatalogue.diff"))
        return findings

COMPONENT = MicrovmDevicesComponent
