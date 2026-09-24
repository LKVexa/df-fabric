"""INV-43 - Transient-execution defense.

Transient-execution defense is the tax every isolation boundary pays after Spectre. Mitigations are not free and not universal, so the honest position is a per-node record of which are active, what they cost, and which trust classes may not be co-located without them.

The component answers all 100 requirements of the INV-43 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

ACTIVE, INACTIVE, UNKNOWN = "active", "inactive", "unknown"

#: Mitigations required before two different tenants may share a node.
REQUIRED_FOR_COTENANCY = ("spectre_v2", "l1tf", "mds", "mmio_stale_data")


class MitigationMissing(PermissionError):
    """Raised when co-tenancy is attempted without the required mitigations."""


@dataclass
class MitigationState:
    """One node's transient-execution posture, as read back rather than assumed."""

    node: str
    #: mitigation -> (status, measured cost percent)
    mitigations: dict = field(default_factory=dict)
    smt_enabled: bool = True
    core_scheduling: bool = False

    def record(self, name: str, status: str, cost_percent: float = 0.0) -> None:
        if status not in (ACTIVE, INACTIVE, UNKNOWN):
            raise ValueError(f"unknown mitigation status: {status!r}")
        if status == ACTIVE and cost_percent <= 0:
            raise ValueError(f"{name}: an active mitigation must carry a measured cost")
        self.mitigations[name] = (status, cost_percent)

    def status(self, name: str) -> str:
        """An unrecorded mitigation is unknown, and unknown is treated as inactive."""
        return self.mitigations.get(name, (UNKNOWN, 0.0))[0]

    def active(self) -> set:
        return {n for n, (s, _) in self.mitigations.items() if s == ACTIVE}

    def total_cost(self) -> float:
        return round(sum(c for s, c in self.mitigations.values() if s == ACTIVE), 2)

    def report(self) -> dict:
        return {"schema": "PK_MITIGATIONS/1", "node": self.node,
                "active": sorted(self.active()),
                "inactive_or_unknown": sorted(
                    n for n in REQUIRED_FOR_COTENANCY if self.status(n) != ACTIVE),
                "total_cost_percent": self.total_cost(),
                "smt_enabled": self.smt_enabled,
                "core_scheduling": self.core_scheduling}

    def may_cotenant(self, tenant_a: str, tenant_b: str) -> dict:
        """Two tenants may share a node only with full mitigations and no bare SMT."""
        if tenant_a == tenant_b:
            return {"schema": "PK_COTENANCY/1", "permitted": True,
                    "reason": "same tenant; no cross-tenant boundary to defend"}
        missing = [m for m in REQUIRED_FOR_COTENANCY if self.status(m) != ACTIVE]
        if missing:
            raise MitigationMissing(
                f"{self.node}: cross-tenant co-tenancy needs {missing} active")
        if self.smt_enabled and not self.core_scheduling:
            raise MitigationMissing(
                f"{self.node}: SMT is enabled without core scheduling; siblings share "
                "microarchitectural state across the tenant boundary")
        return {"schema": "PK_COTENANCY/1", "permitted": True,
                "tenants": sorted([tenant_a, tenant_b]),
                "mitigations": sorted(self.active()),
                "cost_percent": self.total_cost()}


class TransientExecutionDefenseComponent(Component):
    """Master-applied component for INV-43."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        node = MitigationState("n1", smt_enabled=False)
        for name, cost in [("spectre_v2", 3.1), ("l1tf", 1.4), ("mds", 2.0), ("mmio_stale_data", 0.8)]:
            node.record(name, ACTIVE, cost)
        report = node.report()
        assert report["total_cost_percent"] == 7.3 and not report["inactive_or_unknown"]
        assert node.may_cotenant("t1", "t2")["permitted"]
        findings[5] = self.satisfied(
            items[5],
            f"Mitigation state is recorded with measured cost ({report['total_cost_percent']}% total "
            f"across {len(report['active'])} mitigations), so the tax is a number rather than a shrug.",
            *self._evidence("component.py::MitigationState"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        node = MitigationState("n1", smt_enabled=False)
        node.record("spectre_v2", ACTIVE, 3.0)
        try:
            node.may_cotenant("t1", "t2")
        except MitigationMissing:
            findings[5] = self.satisfied(
                items[5],
                "A node missing any required mitigation refuses cross-tenant co-tenancy, so partial "
                "mitigation does not buy partial co-location.",
                *self._evidence("component.py::MitigationState.may_cotenant"))
        full = MitigationState("n2", smt_enabled=True, core_scheduling=False)
        for name in REQUIRED_FOR_COTENANCY:
            full.record(name, ACTIVE, 1.0)
        try:
            full.may_cotenant("t1", "t2")
        except MitigationMissing:
            findings[0] = self.satisfied(
                items[0],
                "Even fully mitigated, SMT without core scheduling blocks cross-tenant co-tenancy, because "
                "siblings share microarchitectural state the mitigations do not cover.",
                *self._evidence("component.py::MitigationState.may_cotenant"))
        assert full.status("some_future_class") == UNKNOWN
        findings[9] = self.satisfied(
            items[9],
            "An unrecorded mitigation reads as unknown and is treated as inactive, so a new attack class "
            "is not assumed covered by the mitigations already in place.",
            *self._evidence("component.py::MitigationState.status"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        node = MitigationState("n1")
        try:
            node.record("spectre_v2", ACTIVE, 0.0)
        except ValueError:
            findings[6] = self.satisfied(
                items[6],
                "A mitigation cannot be recorded active without a measured cost, so the performance tax is "
                "always exported alongside the protection.",
                *self._evidence("component.py::MitigationState.record"))
        return findings

COMPONENT = TransientExecutionDefenseComponent
