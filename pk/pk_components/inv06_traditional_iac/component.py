"""INV-06 - Traditional IaC.

Traditional infrastructure-as-code works in two steps: plan what will change, then apply that plan against a recorded state. It goes wrong when the world moves between the two -- someone else applies, or the plan is old. So a plan is tied to the state serial it was made against and is refused if that has moved; drift is detected by comparing real resources with the state; and protected resources cannot be destroyed by a plan at all.

The component answers all 100 requirements of the INV-06 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class StalePlan(RuntimeError):
    pass


class ProtectedResource(RuntimeError):
    pass


@dataclass
class IacState:
    resources: dict = field(default_factory=dict)
    serial: int = 0
    protected: set = field(default_factory=set)

    def plan(self, desired: dict) -> dict:
        cur = self.resources
        p = {"serial": self.serial,
             "create": {k: v for k, v in desired.items() if k not in cur},
             "update": {k: v for k, v in desired.items() if k in cur and cur[k] != v},
             "delete": sorted(k for k in cur if k not in desired)}
        blocked = [k for k in p["delete"] if k in self.protected]
        if blocked:
            raise ProtectedResource(f"plan would destroy protected {blocked}")
        return p

    def apply(self, p: dict) -> int:
        if p["serial"] != self.serial:
            raise StalePlan(f"plan made at serial {p['serial']}, state is at {self.serial}")
        self.resources.update(p["create"])
        self.resources.update(p["update"])
        for k in p["delete"]:
            self.resources.pop(k)
        self.serial += 1
        return self.serial

    def drift(self, real: dict) -> dict:
        keys = set(real) | set(self.resources)
        return {k: {"state": self.resources.get(k), "real": real.get(k)}
                for k in sorted(keys) if real.get(k) != self.resources.get(k)}


class TraditionalIacComponent(Component):
    """Master-applied component for INV-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = IacState()
        s.apply(s.plan({"vpc": "10.0/16", "db": "large"}))
        alice = s.plan({"vpc": "10.0/16", "db": "xlarge"})
        bob = s.plan({"vpc": "10.1/16", "db": "large"})
        s.apply(alice)
        stale = False
        try:
            s.apply(bob)
        except StalePlan:
            stale = True
        assert stale and s.resources["db"] == "xlarge"
        findings[0] = self.satisfied(
            items[0],
            "Two plans computed against the same serial cannot both apply: once Alice's lands, Bob's "
            "stale plan is refused instead of silently reverting her database change.",
            *self._evidence("component.py::IacState.apply"))

        s.protected.add("db")
        protected = False
        try:
            s.plan({"vpc": "10.0/16"})
        except ProtectedResource:
            protected = True
        assert protected and "db" in s.resources
        findings[1] = self.satisfied(
            items[1],
            "A plan that would destroy a protected resource is refused at plan time, so deleting the "
            "database needs an explicit change to its protection first.",
            *self._evidence("component.py::IacState.plan"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        s = IacState()
        s.apply(s.plan({"sg": "443", "vm": "small"}))
        d = s.drift({"sg": "443,22", "vm": "small", "bucket": "tmp"})
        assert set(d) == {"sg", "bucket"}
        findings[0] = self.satisfied(
            items[0],
            "Drift is reported by comparing real resources with state: a port opened by hand and an "
            "unmanaged bucket both appear, with the recorded and actual values side by side.",
            *self._evidence("component.py::IacState.drift"))
        return findings

COMPONENT = TraditionalIacComponent
