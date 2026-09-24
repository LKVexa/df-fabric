"""INV-30 - Capability hardware sandbox.

The capability hardware sandbox is CHERI-shaped: pointers carry bounds and permissions the hardware itself checks, so a bug cannot be turned into an arbitrary write. It is the one tier where memory safety is enforced below the software stack -- and it exists on very little hardware, which this element states rather than glosses over.

The component answers all 100 requirements of the INV-30 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

PERMISSIONS = frozenset({"read", "write", "execute"})


class BoundsViolation(PermissionError):
    """Raised when an access falls outside a capability's bounds."""


class PermissionViolation(PermissionError):
    """Raised when an operation needs a permission the capability does not carry."""


class Amplification(PermissionError):
    """Raised when a derivation would widen bounds or permissions."""


class Invalidated(PermissionError):
    """Raised when an invalidated capability is used."""


@dataclass
class Capability:
    """A hardware-checked memory capability: bounds and permissions travel with the pointer."""

    base: int
    length: int
    permissions: frozenset
    valid: bool = True

    def __post_init__(self):
        unknown = set(self.permissions) - PERMISSIONS
        if unknown:
            raise ValueError(f"unknown permissions: {sorted(unknown)}")
        if self.length < 0:
            raise ValueError("capability length may not be negative")

    @property
    def limit(self) -> int:
        return self.base + self.length

    def derive(self, *, base: int, length: int, permissions=None) -> "Capability":
        """Derive a narrower capability. Widening in any dimension is refused."""
        if not self.valid:
            raise Invalidated("cannot derive from an invalidated capability")
        perms = frozenset(permissions) if permissions is not None else self.permissions
        if base < self.base or base + length > self.limit:
            raise Amplification(
                f"derived bounds [{base}, {base + length}) escape [{self.base}, {self.limit})")
        if not perms <= self.permissions:
            raise Amplification(
                f"derived permissions {sorted(perms - self.permissions)} exceed the held set")
        return Capability(base, length, perms)

    def check(self, *, address: int, size: int, operation: str) -> dict:
        if not self.valid:
            raise Invalidated("capability has been invalidated")
        if operation not in self.permissions:
            raise PermissionViolation(
                f"{operation!r} not permitted by this capability ({sorted(self.permissions)})")
        if address < self.base or address + size > self.limit:
            raise BoundsViolation(
                f"access [{address}, {address + size}) escapes [{self.base}, {self.limit})")
        return {"schema": "PK_CAPABILITY_ACCESS/1", "address": address, "size": size,
                "operation": operation, "permitted": True}

    def invalidate(self) -> None:
        """Invalidation is permanent; there is no path back to valid."""
        self.valid = False


class CapabilityHardwareSandboxComponent(Component):
    """Master-applied component for INV-30."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        root = Capability(0x1000, 0x1000, frozenset({"read", "write"}))
        child = root.derive(base=0x1400, length=0x200, permissions={"read"})
        assert child.base == 0x1400 and child.permissions == frozenset({"read"})
        assert child.check(address=0x1400, size=16, operation="read")["permitted"]
        findings[5] = self.satisfied(
            items[5],
            f"Derivation narrows in both dimensions at once: [{hex(root.base)}, {hex(root.limit)}) with "
            f"read+write became [{hex(child.base)}, {hex(child.limit)}) with read only.",
            *self._evidence("component.py::Capability.derive"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        root = Capability(0x1000, 0x1000, frozenset({"read"}))
        proven = []
        try:
            root.derive(base=0x800, length=0x100)
        except Amplification:
            proven.append("bounds widening")
        try:
            root.derive(base=0x1000, length=0x10, permissions={"read", "write"})
        except Amplification:
            proven.append("permission amplification")
        try:
            root.check(address=0x2000, size=8, operation="read")
        except BoundsViolation:
            proven.append("out-of-bounds access")
        try:
            root.check(address=0x1000, size=8, operation="write")
        except PermissionViolation:
            proven.append("missing permission")
        assert len(proven) == 4, proven
        findings[1] = self.satisfied(
            items[1],
            f"All four amplification paths are refused: {', '.join(proven)}. Authority is monotonically "
            "decreasing by construction, which is the whole point of the tier.",
            *self._evidence("component.py::Capability"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        cap = Capability(0x1000, 0x100, frozenset({"read"}))
        cap.invalidate()
        proven = []
        try:
            cap.check(address=0x1000, size=8, operation="read")
        except Invalidated:
            proven.append("access")
        try:
            cap.derive(base=0x1000, length=0x10)
        except Invalidated:
            proven.append("derivation")
        assert len(proven) == 2
        findings[6] = self.satisfied(
            items[6],
            "Invalidation is permanent and closes both access and derivation, so a freed capability cannot "
            "be resurrected into a use-after-free.",
            *self._evidence("component.py::Capability.invalidate"))
        gap02 = sibling("GAP-02")
        if gap02 is None:
            findings[0] = self.partial(
                items[0],
                "This element models the capability semantics but cannot tell whether the node has the "
                "hardware.",
                note="GAP-02 Hardware capability discovery is not installed here")
        else:
            report = gap02.CapabilityReport("n1")
            def no_cheri():
                raise gap02.ProbeUnavailable("no capability hardware on this node")
            assert gap02.probe(report, "cheri", no_cheri, 0) == gap02.UNPROBED
            view = report.for_consumer(now=1)
            assert "cheri" not in view["present"] and "cheri" in view["unprobed"]
            gap02.probe(report, "cheri", lambda: True, 2)
            assert "cheri" in report.for_consumer(now=3)["present"]
            findings[0] = self.satisfied(
                items[0],
                "Tier availability is decided by a real GAP-02 probe rather than assumed: an unprobeable "
                "node publishes capability hardware as unprobed and the tier is invisible to placement, "
                "while a node that probes positive makes it available.",
                *self._evidence("contract.py"), "GAP-02/CapabilityReport")
        return findings

COMPONENT = CapabilityHardwareSandboxComponent
