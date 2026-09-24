"""INV-08 - Dynamic infrastructure model.

The dynamic infrastructure model treats capacity as something borrowed, not owned: nodes join a pool on a lease, are reclaimed when the lease lapses, and the pool grows and shrinks between hard bounds as demand changes. Two things must never happen -- unbounded growth, and a node reclaimed while it is still running work.

The component answers all 100 requirements of the INV-08 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import math
from dataclasses import dataclass, field


@dataclass
class Pool:
    min_nodes: int
    max_nodes: int
    per_node: int = 4
    lease_ttl: int = 10
    nodes: dict = field(default_factory=dict)       # node -> {"expires", "busy"}
    _n: int = 0
    node_hours: int = 0

    def tick(self, now: int, demand: int) -> dict:
        self.node_hours += len(self.nodes)
        for n, v in self.nodes.items():
            if v["busy"]:
                v["expires"] = now + self.lease_ttl            # renew busy nodes
        want = max(self.min_nodes, min(self.max_nodes, math.ceil(demand / self.per_node)))
        added = 0
        while len(self.nodes) < want:
            self._n += 1
            self.nodes[f"node-{self._n}"] = {"expires": now + self.lease_ttl, "busy": False}
            added += 1
        reclaimed = []
        for n, v in sorted(self.nodes.items()):
            surplus = len(self.nodes) > want
            if not v["busy"] and (v["expires"] <= now or surplus):
                reclaimed.append(n)
                del self.nodes[n]
        return {"size": len(self.nodes), "added": added, "reclaimed": reclaimed}


class DynamicInfrastructureModelComponent(Component):
    """Master-applied component for INV-08."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Pool(min_nodes=1, max_nodes=5)
        spike = p.tick(0, demand=1000)
        assert spike["size"] == 5
        busy = sorted(p.nodes)[:2]
        for n in busy:
            p.nodes[n]["busy"] = True
        calm = p.tick(20, demand=0)
        assert all(n in p.nodes for n in busy) and calm["size"] == 2
        findings[0] = self.satisfied(
            items[0],
            "A demand spike of 1000 units grows the pool only to its 5-node bound; when demand drops, "
            "idle nodes are reclaimed but the two nodes still running work keep renewed leases and stay.",
            *self._evidence("component.py::Pool.tick"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        p = Pool(min_nodes=1, max_nodes=10)
        sizes = [p.tick(t, d)["size"] for t, d in enumerate([4, 16, 40, 8, 0, 0])]
        assert sizes == [1, 4, 10, 2, 1, 1]
        findings[0] = self.satisfied(
            items[0],
            f"Pool size follows demand within bounds ({sizes}) and falls back to the minimum when idle, "
            f"so cost ({p.node_hours} node-ticks) tracks use rather than peak.",
            *self._evidence("component.py::Pool.tick"))
        return findings

COMPONENT = DynamicInfrastructureModelComponent
