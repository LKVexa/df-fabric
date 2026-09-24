"""INV-63 - Wasm deployment manager.

The Wasm deployment manager holds desired state -- which components, how many, spread across which labels -- and reconciles the lattice toward it. Its guarantees are convergence (repeated reconciliation reaches the desired state and then does nothing) and safe rollout (never more than the allowed number of instances unavailable while a version changes).

The component answers all 100 requirements of the INV-63 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Manager:
    hosts: dict                                  # host -> zone
    actual: list = field(default_factory=list)   # [(component, version, host)]

    def diff(self, component, version, count, spread=True):
        mine = [a for a in self.actual if a[0] == component]
        stale = [a for a in mine if a[1] != version]
        good = [a for a in mine if a[1] == version]
        stops = list(stale) + good[count:]
        good = good[:count]
        starts = []
        zones = Counter(self.hosts[h] for _, _, h in good)
        hosts = sorted(self.hosts)
        while len(good) + len(starts) < count:
            if spread:
                host = min(hosts, key=lambda h: (zones[self.hosts[h]], h))
            else:
                host = hosts[0]
            zones[self.hosts[host]] += 1
            starts.append((component, version, host))
        return {"start": starts, "stop": stops}

    def apply(self, d):
        for s in d["stop"]:
            self.actual.remove(s)
        self.actual.extend(d["start"])

    def rollout(self, component, version, max_unavailable=1):
        """Replace old instances in batches; never more than max_unavailable down at once."""
        batches, worst = 0, 0
        while True:
            old = [a for a in self.actual if a[0] == component and a[1] != version][:max_unavailable]
            if not old:
                return batches, worst
            total = sum(1 for a in self.actual if a[0] == component)
            for o in old:
                self.actual.remove(o)
            worst = max(worst, total - sum(1 for a in self.actual if a[0] == component))
            for o in old:
                self.actual.append((component, version, o[2]))
            batches += 1


class WasmDeploymentManagerComponent(Component):
    """Master-applied component for INV-63."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        m = Manager({"h1": "z1", "h2": "z1", "h3": "z2", "h4": "z3"})
        d = m.diff("api", "v1", 3)
        m.apply(d)
        zones = {m.hosts[h] for _, _, h in m.actual}
        again = m.diff("api", "v1", 3)
        assert len(d["start"]) == 3 and zones == {"z1", "z2", "z3"} and again == {"start": [], "stop": []}
        findings[0] = self.satisfied(
            items[0],
            "Reconciliation starts three instances spread across three zones, and a second reconcile "
            "against the converged lattice emits no actions -- the manager converges and then rests.",
            *self._evidence("component.py::Manager.diff"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        m = Manager({f"h{i}": f"z{i}" for i in range(4)})
        m.apply(m.diff("api", "v1", 4))
        batches, worst = m.rollout("api", "v2", max_unavailable=1)
        assert batches == 4 and worst == 1 and all(v == "v2" for _, v, _ in m.actual)
        findings[0] = self.satisfied(
            items[0],
            f"A version rollout across 4 instances proceeds in {batches} batches with at most {worst} "
            "instance unavailable at any time, ending with every instance on the new version.",
            *self._evidence("component.py::Manager.rollout"))
        return findings

COMPONENT = WasmDeploymentManagerComponent
