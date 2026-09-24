"""INV-23 - Hardware virtualization primitive.

The hardware virtualization primitive is the floor everything above it stands on: the CPU's own trap-and-emulate machinery. It is either present and usable or it is not, and no amount of software above it can manufacture it, so this element reports it honestly and refuses to pretend nested virtualization is the same thing as bare metal.

The component answers all 100 requirements of the INV-23 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass

USABLE, PRESENT_DISABLED, ABSENT, CLAIMED = "usable", "present-disabled", "absent", "claimed"


class PrimitiveUnavailable(RuntimeError):
    """Raised when the virtualization primitive cannot be claimed for use."""


@dataclass
class VirtPrimitive:
    """The host CPU's virtualization extension, as probed rather than as advertised."""

    host: str
    cpuid_present: bool = False
    firmware_enabled: bool = False
    device_openable: bool = False
    nesting_depth: int = 0          # 0 = bare metal, 1 = we are a guest, ...
    holder: str | None = None

    def state(self) -> str:
        """Usability is proven by the device, never inferred from CPUID."""
        if not self.cpuid_present:
            return ABSENT
        if not self.firmware_enabled or not self.device_openable:
            return PRESENT_DISABLED
        if self.holder is not None:
            return CLAIMED
        return USABLE

    def claim(self, holder: str, *, max_nesting: int = 1) -> dict:
        state = self.state()
        if state != USABLE:
            raise PrimitiveUnavailable(f"{self.host}: virtualization primitive is {state}")
        if self.nesting_depth > max_nesting:
            raise PrimitiveUnavailable(
                f"{self.host}: nesting depth {self.nesting_depth} exceeds the permitted {max_nesting}")
        self.holder = holder
        return {"schema": "PK_VIRT_CLAIM/1", "host": self.host, "holder": holder,
                "nesting_depth": self.nesting_depth,
                "bare_metal": self.nesting_depth == 0}

    def release(self) -> None:
        self.holder = None

    def report(self) -> dict:
        return {"schema": "PK_VIRT_PRIMITIVE/1", "host": self.host, "state": self.state(),
                "nesting_depth": self.nesting_depth,
                "bare_metal": self.nesting_depth == 0 and self.state() == USABLE}


class HardwareVirtualizationPrimitiveComponent(Component):
    """Master-applied component for INV-23."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        bare = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        assert bare.state() == USABLE and bare.report()["bare_metal"]
        disabled = VirtPrimitive("n2", cpuid_present=True, firmware_enabled=False)
        assert disabled.state() == PRESENT_DISABLED
        assert VirtPrimitive("n3").state() == ABSENT
        findings[5] = self.satisfied(
            items[5],
            "Detection is three-valued: usable, present-but-disabled and absent are distinct states, and "
            "only a device that actually opens reports usable.",
            *self._evidence("component.py::VirtPrimitive.state"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        p.claim("vmm-a")
        try:
            p.claim("vmm-b")
        except PrimitiveUnavailable:
            findings[5] = self.satisfied(
                items[5],
                "The virtualization device is exclusive: a second hypervisor cannot claim it, so two VMMs "
                "cannot believe they own the same CPU.",
                *self._evidence("component.py::VirtPrimitive.claim"))
        nested = VirtPrimitive("n2", cpuid_present=True, firmware_enabled=True,
                               device_openable=True, nesting_depth=2)
        assert not nested.report()["bare_metal"]
        try:
            nested.claim("vmm", max_nesting=1)
        except PrimitiveUnavailable:
            findings[0] = self.satisfied(
                items[0],
                "A host already nested two levels deep cannot claim the primitive under a depth-1 policy, "
                "so a guest cannot present nested execution as bare-metal isolation.",
                *self._evidence("component.py::VirtPrimitive.claim"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        p.claim("vmm")
        p.firmware_enabled = False          # firmware downgrade between probes
        assert p.state() == PRESENT_DISABLED
        findings[3] = self.satisfied(
            items[3],
            "A firmware downgrade flips the primitive back to present-disabled on the next probe rather "
            "than leaving a stale usable verdict behind.",
            *self._evidence("component.py::VirtPrimitive.state"))
        return findings

COMPONENT = HardwareVirtualizationPrimitiveComponent
