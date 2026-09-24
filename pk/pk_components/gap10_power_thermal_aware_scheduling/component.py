"""GAP-10 - Power/thermal-aware scheduling.

Power and thermal-aware scheduling is the constraint a data-centre scheduler never had to model. An edge node in a hot cabinet on a battery cannot run what a racked node can, and this element makes that a hard ceiling the scheduler cannot argue with.

The component answers all 100 requirements of the GAP-10 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass

#: Temperature thresholds in degrees Celsius.
NOMINAL, ELEVATED, CRITICAL, EMERGENCY = 60.0, 75.0, 85.0, 95.0

#: Ceiling as a fraction of full capacity at each band.
BAND_CEILING = {"nominal": 1.0, "elevated": 0.6, "critical": 0.25, "emergency": 0.0}

#: Degrees a node must cool below a threshold before it recovers -- hysteresis.
RECOVERY_MARGIN = 5.0

#: Fraction of battery held in reserve; below this the node sheds to critical.
BATTERY_RESERVE = 0.15


@dataclass
class ThermalState:
    """One node's power and thermal position, and the ceiling it implies."""

    node: str
    temperature: float | None = None      # None means no usable sensor evidence
    battery: float | None = None          # fraction remaining, None when mains-powered
    band: str = "nominal"

    def _raw_band(self) -> str:
        if self.temperature is None:
            # No evidence is not evidence of cool: fall to the critical band.
            return "critical"
        if self.temperature >= EMERGENCY:
            return "emergency"
        if self.temperature >= CRITICAL:
            return "critical"
        if self.temperature >= ELEVATED:
            return "elevated"
        return "nominal"

    def update(self, *, temperature: float | None, battery: float | None = None) -> str:
        """Apply a reading with hysteresis: escalate immediately, recover slowly."""
        self.temperature, self.battery = temperature, battery
        proposed = self._raw_band()
        order = ("nominal", "elevated", "critical", "emergency")
        if order.index(proposed) > order.index(self.band):
            self.band = proposed                      # heating: act at once
        elif order.index(proposed) < order.index(self.band) and temperature is not None:
            floor = {"elevated": ELEVATED, "critical": CRITICAL, "emergency": EMERGENCY}[self.band]
            if temperature <= floor - RECOVERY_MARGIN:
                self.band = proposed                  # cooling: only past the margin
        if battery is not None and battery < BATTERY_RESERVE and self.band == "nominal":
            self.band = "critical"
        return self.band

    def ceiling(self, full_capacity: int) -> dict:
        fraction = BAND_CEILING[self.band]
        slots = int(full_capacity * fraction)
        return {"schema": "PK_POWER_CEILING/1", "node": self.node, "band": self.band,
                "ceiling": slots, "excluded": self.band == "emergency",
                "reason": ("no thermal evidence" if self.temperature is None
                           else f"{self.temperature:.1f}C in band {self.band}")}


class PowerThermalAwareSchedulingComponent(Component):
    """Master-applied component for GAP-10."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        t = ThermalState("n1")
        assert t.update(temperature=40.0) == "nominal"
        assert t.ceiling(10)["ceiling"] == 10
        assert t.update(temperature=80.0) == "elevated"
        assert t.ceiling(10)["ceiling"] == 6
        assert t.update(temperature=96.0) == "emergency"
        assert t.ceiling(10)["excluded"] and t.ceiling(10)["ceiling"] == 0
        findings[5] = self.satisfied(
            items[5],
            "Ceilings fall monotonically with temperature and reach zero with exclusion at the emergency "
            "threshold.",
            *self._evidence("component.py::ThermalState.ceiling"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        blind = ThermalState("n1")
        assert blind.update(temperature=None) == "critical"
        assert blind.ceiling(10)["ceiling"] == 2
        findings[7] = self.satisfied(
            items[7],
            "A node with no thermal evidence falls to the critical band, so suppressing a sensor reduces a "
            "node's share rather than hiding an overheating one.",
            *self._evidence("component.py::ThermalState._raw_band"))
        hot = ThermalState("n2")
        hot.update(temperature=96.0)
        assert hot.ceiling(100)["excluded"], "emergency node was not excluded"
        findings[5] = self.satisfied(
            items[5],
            "Exclusion is a node-level verdict applied to every tenant and class alike; no workload is "
            "exempt from a thermal ceiling.",
            *self._evidence("component.py::ThermalState.ceiling"))
        gap09 = sibling("GAP-09")
        if gap09 is None:
            findings[0] = self.partial(
                items[0], "Thermal readings are trusted as supplied and cannot be authenticated here.",
                note="GAP-09 Unified observability is not installed here")
        else:
            store = gap09.SignalStore()
            cool = gap09.Sample("temperature", 30.0, "t1", "dub", "n1", at=0)
            try:
                store.submit("rogue", [cool], attested_level="untrusted", signed=True, now=0)
                forged = True
            except gap09.ReporterUntrusted:
                forged = False
            assert not forged, "an unattested reporter injected a cool reading"
            store.submit("n1", [gap09.Sample("temperature", 96.0, "t1", "dub", "n1", at=0)],
                         attested_level="hardware", signed=True, now=0)
            reading = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="n1",
                                 signal="temperature", now=1)
            state = ThermalState("n1")
            state.update(temperature=reading["value"])
            assert state.ceiling(10)["excluded"]
            findings[0] = self.satisfied(
                items[0],
                "Thermal readings arrive through GAP-09, which refuses unattested reporters, so a forged "
                "cool reading cannot keep an overheating node in service; the authenticated 96C reading "
                "excluded the node.",
                *self._evidence("component.py::ThermalState.update"), "GAP-09/SignalStore")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        t = ThermalState("n1")
        t.update(temperature=86.0)
        assert t.band == "critical"
        assert t.update(temperature=84.0) == "critical", "recovered before the hysteresis margin"
        assert t.update(temperature=CRITICAL - RECOVERY_MARGIN - 0.1) == "elevated"
        findings[5] = self.satisfied(
            items[5],
            f"Recovery requires cooling {RECOVERY_MARGIN}C below the threshold, so a node hovering at the "
            "boundary does not flap in and out of service.",
            *self._evidence("component.py::ThermalState.update"))
        battery = ThermalState("n3")
        assert battery.update(temperature=30.0, battery=0.10) == "critical"
        findings[1] = self.satisfied(
            items[1],
            "A cool node below its battery reserve still sheds to the critical band: energy budget is a "
            "constraint in its own right, not a side effect of heat.",
            *self._evidence("component.py::ThermalState.update"))
        return findings

COMPONENT = PowerThermalAwareSchedulingComponent
