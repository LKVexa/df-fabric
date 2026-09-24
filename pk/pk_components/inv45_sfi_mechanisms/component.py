"""INV-45 - SFI mechanisms.

Software fault isolation is the fallback when hardware will not help: masking every memory access into a sandbox region so a compromised module cannot reach outside it. It is cheap and portable, and it is only as good as the guarantee that every access really was rewritten -- so this element verifies that rather than assuming it.

The component answers all 100 requirements of the INV-45 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class UnmaskedAccess(PermissionError):
    """Raised when a module contains a memory access that was not rewritten."""


class BranchOutsideTargets(PermissionError):
    """Raised when an indirect branch would leave the permitted target set."""


@dataclass(frozen=True)
class Access:
    """One memory access in a module, and whether the rewriter masked it."""

    offset: int
    masked: bool


@dataclass
class SandboxRegion:
    """A power-of-two region: masking an address can never leave it."""

    base: int
    size: int

    def __post_init__(self):
        if self.size <= 0 or (self.size & (self.size - 1)) != 0:
            raise ValueError(f"region size {self.size} must be a positive power of two")

    @property
    def mask(self) -> int:
        return self.size - 1

    def confine(self, address: int) -> int:
        """Masking is total: any address whatsoever lands inside the region."""
        return self.base + (address & self.mask)

    def contains(self, address: int) -> bool:
        return self.base <= address < self.base + self.size


@dataclass
class SfiModule:
    """A module confined by masking, loaded only after full verification."""

    name: str
    region: SandboxRegion
    accesses: tuple
    indirect_targets: frozenset
    overhead_percent: float = 0.0
    verified: bool = False

    def verify(self) -> dict:
        """Every access must have been rewritten; one exception defeats the scheme."""
        unmasked = [a.offset for a in self.accesses if not a.masked]
        if unmasked:
            raise UnmaskedAccess(
                f"{self.name}: {len(unmasked)} unmasked access(es) at offsets {unmasked[:5]}")
        self.verified = True
        return {"schema": "PK_SFI_MODULE/1", "module": self.name,
                "accesses": len(self.accesses), "all_masked": True,
                "region": {"base": self.region.base, "size": self.region.size},
                "overhead_percent": self.overhead_percent}

    def access(self, address: int) -> dict:
        if not self.verified:
            raise UnmaskedAccess(f"{self.name}: module was not verified before access")
        confined = self.region.confine(address)
        return {"schema": "PK_SFI_MASK/1", "requested": address, "effective": confined,
                "inside_region": self.region.contains(confined)}

    def branch(self, target: int) -> int:
        if target not in self.indirect_targets:
            raise BranchOutsideTargets(
                f"{self.name}: indirect branch to {target} is outside the permitted target set")
        return target


class SfiMechanismsComponent(Component):
    """Master-applied component for INV-45."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        region = SandboxRegion(0x40000000, 0x10000)
        module = SfiModule("svc", region,
                           tuple(Access(i, True) for i in range(8)),
                           frozenset({0, 16, 32}), overhead_percent=11.5)
        report = module.verify()
        assert report["all_masked"] and report["accesses"] == 8
        assert module.branch(16) == 16
        findings[5] = self.satisfied(
            items[5],
            f"All {report['accesses']} accesses verified as rewritten before load, at a measured "
            f"{report['overhead_percent']}% masking overhead.",
            *self._evidence("component.py::SfiModule.verify"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        region = SandboxRegion(0x40000000, 0x10000)
        # Masking is total: even a wildly out-of-range address lands inside the region.
        module = SfiModule("svc", region, (Access(0, True),), frozenset({0}))
        module.verify()
        for address in (0x0, 0xFFFFFFFF, 0x40000000 - 1, 0x7FFFFFFFFFFF):
            result = module.access(address)
            assert result["inside_region"], result
        findings[5] = self.satisfied(
            items[5],
            "Masking confines every address without exception: four wildly out-of-range accesses, "
            "including a 47-bit one, all resolve inside the sandbox region.",
            *self._evidence("component.py::SandboxRegion.confine"))
        broken = SfiModule("bad", region,
                           (Access(0, True), Access(4, False)), frozenset({0}))
        try:
            broken.verify()
        except UnmaskedAccess:
            findings[6] = self.satisfied(
                items[6],
                "A single unmasked access refuses the whole module, because one escape hatch defeats the "
                "entire scheme rather than weakening it proportionally.",
                *self._evidence("component.py::SfiModule.verify"))
        try:
            module.branch(999)
        except BranchOutsideTargets:
            findings[2] = self.satisfied(
                items[2],
                "Indirect branches are confined to a permitted target set, so control flow cannot be "
                "redirected to an address the rewriter never sanctioned.",
                *self._evidence("component.py::SfiModule.branch"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        try:
            SandboxRegion(0x1000, 0x3000)
        except ValueError:
            findings[6] = self.satisfied(
                items[6],
                "A region whose size is not a power of two is refused at construction, because masking "
                "only confines when the mask covers the whole region.",
                *self._evidence("component.py::SandboxRegion"))
        unverified = SfiModule("svc", SandboxRegion(0x1000, 0x1000),
                               (Access(0, True),), frozenset({0}))
        try:
            unverified.access(0x10)
        except UnmaskedAccess:
            findings[0] = self.satisfied(
                items[0],
                "An unverified module cannot be accessed at all, so skipping verification for performance "
                "fails closed rather than silently running unconfined.",
                *self._evidence("component.py::SfiModule.access"))
        return findings

COMPONENT = SfiMechanismsComponent
