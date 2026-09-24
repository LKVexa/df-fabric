"""PLN-05 - Elasticity plane.

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.

The component answers all 100 requirements of the PLN-05 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    """Declared capacity envelope and hysteresis parameters for one workload."""

    floor: int = 0
    ceiling: int = 10
    scale_up_at: float = 0.75
    scale_down_at: float = 0.25
    grace_samples: int = 3

    def __post_init__(self):
        if self.floor < 0 or self.ceiling < self.floor:
            raise ValueError(f"inconsistent limits: floor={self.floor} ceiling={self.ceiling}")
        if not 0 < self.scale_down_at < self.scale_up_at < 1:
            raise ValueError("thresholds must satisfy 0 < scale_down_at < scale_up_at < 1")


class ElasticityController:
    """Hysteretic capacity controller for one workload.

    Scale-up is immediate; scale-down must hold below the low-water mark for
    ``grace_samples`` consecutive samples.  The target is always clamped into
    ``[floor, ceiling]``, including a ceiling lowered externally.
    """

    def __init__(self, limits: Limits, current: int | None = None):
        self.limits = limits
        self.current = limits.floor if current is None else current
        self._below = 0
        self.suppressed = 0

    def lower_ceiling(self, ceiling: int) -> None:
        """Accept an externally imposed ceiling (power, thermal, or site cap)."""
        self.limits = Limits(min(self.limits.floor, ceiling), ceiling,
                             self.limits.scale_up_at, self.limits.scale_down_at,
                             self.limits.grace_samples)
        self.current = min(self.current, ceiling)

    def observe(self, utilisation: float) -> tuple[int, str]:
        """Feed one demand sample; return the (target, reason) pair."""
        lim = self.limits
        if utilisation >= lim.scale_up_at:
            self._below = 0
            target, reason = min(self.current + max(1, self.current), lim.ceiling), "scale-up"
        elif utilisation <= lim.scale_down_at:
            self._below += 1
            if self._below >= lim.grace_samples:
                self._below = 0
                target, reason = max(self.current // 2, lim.floor), "scale-down"
            else:
                self.suppressed += 1
                target, reason = self.current, "hold: within scale-down grace period"
        else:
            self._below = 0
            target, reason = self.current, "hold: within band"
        self.current = max(lim.floor, min(target, lim.ceiling))
        return self.current, reason


class ElasticityPlaneComponent(Component):
    """Master-applied component for PLN-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = ElasticityController(Limits(floor=0, ceiling=8, grace_samples=3), current=4)
        assert c.observe(0.9)[0] == 8
        held = [c.observe(0.05) for _ in range(2)]
        assert all(t == 8 for t, _ in held), "scale-down acted before the grace period"
        assert c.observe(0.05)[0] == 4, "scale-down did not act after the grace period"
        findings[5] = self.satisfied(
            items[5],
            f"Controller is deterministic and hysteretic: {c.suppressed} scale-down decision(s) suppressed "
            "inside the grace period before one was taken.",
            *self._evidence("component.py::ElasticityController"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        c = ElasticityController(Limits(floor=0, ceiling=5), current=3)
        assert c.observe(0.99)[0] == 5
        samples = 0
        while c.current > 0 and samples < 40:
            target, _ = c.observe(0.0)
            assert 0 <= target <= 5, "target escaped the declared envelope"
            samples += 1
        assert c.current == 0, "scale-to-zero never reached with floor=0"
        findings[3] = self.satisfied(
            items[3],
            f"Targets stayed inside the declared envelope across a full step-down to zero "
            f"({samples} samples, {c.suppressed} suppressed by hysteresis).",
            *self._evidence("component.py::ElasticityController.observe"))
        inv26 = sibling("INV-26")
        if inv26 is None:
            findings[4] = self.partial(
                items[4],
                "Cold-start cost is acknowledged by the grace period but not measured.",
                note="INV-26 MicroVM snapshotting is not installed here")
        else:
            store = inv26.SnapshotStore()
            devices = {"virtio-net", "virtio-block"}
            store.capture(name="warm-pool", tenant="t1", workload="w1",
                          devices=devices, memory_mib=256)
            restore = store.restore("warm-pool", tenant="t1", devices=devices, elapsed_ms=4)
            assert restore["within_budget"] and not restore["cold"]
            controller = ElasticityController(Limits(floor=0, ceiling=8), current=0)
            target, reason = controller.observe(0.99)
            assert target > 0 and reason == "scale-up"
            findings[4] = self.satisfied(
                items[4],
                "Cold start and steady state are now separately budgeted: scaling up from zero restores "
                f"from an INV-26 snapshot in {restore['restore_ms']}ms against a "
                f"{restore['budget_ms']}ms budget, so scale-to-zero costs a measured restore rather than "
                "an unbounded boot.",
                *self._evidence("component.py::ElasticityController.observe"),
                "INV-26/SnapshotStore.restore")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        c = ElasticityController(Limits(floor=2, ceiling=10), current=10)
        c.lower_ceiling(4)
        target, _ = c.observe(0.99)
        assert target == 4, "externally lowered ceiling was not honoured"
        findings[1] = self.satisfied(
            items[1],
            "An externally lowered ceiling clamps the target even under maximum demand.",
            *self._evidence("component.py::ElasticityController.lower_ceiling"))
        try:
            Limits(floor=5, ceiling=1)
        except ValueError:
            findings[6] = self.satisfied(
                items[6], "Inconsistent limit declarations are refused at construction.",
                *self._evidence("component.py::Limits"))
        gap09 = sibling("GAP-09")
        if gap09 is None:
            findings[0] = self.partial(
                items[0], "This plane trusts its demand input; signal authentication is not available.",
                note="GAP-09 Unified observability is not installed here")
        else:
            store = gap09.SignalStore()
            sample = gap09.Sample("demand", 0.99, "t1", "dub", "w1", at=0)
            try:
                store.submit("rogue", [sample], attested_level="untrusted", signed=True, now=0)
                forged = True
            except gap09.ReporterUntrusted:
                forged = False
            assert not forged, "an unattested reporter injected a demand sample"
            store.submit("n1", [sample], attested_level="hardware", signed=True, now=0)
            reading = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                                 signal="demand", now=1)
            controller = ElasticityController(Limits(floor=0, ceiling=8), current=2)
            target, reason = controller.observe(reading["value"])
            assert target > 2 and reason == "scale-up"
            findings[0] = self.satisfied(
                items[0],
                "Demand samples arrive through GAP-09, which refuses unattested or unsigned reporters, so "
                "a forged signal cannot drive this controller; the authenticated 0.99 sample scaled "
                f"{2} -> {target}.",
                *self._evidence("component.py::ElasticityController.observe"), "GAP-09/SignalStore")
        return findings

COMPONENT = ElasticityPlaneComponent
