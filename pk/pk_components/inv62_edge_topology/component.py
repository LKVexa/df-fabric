"""INV-62 - Edge topology.

Edge topology is the shape of the estate: cloud regions, sites, and devices at the far end, connected by links of very different latency and reliability. This element keeps that graph, answers 'what is nearest that can serve this?', and keeps a site working when its uplink goes -- a partitioned site elects a local coordinator instead of stopping.

The component answers all 100 requirements of the INV-62 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import heapq
from dataclasses import dataclass, field


@dataclass
class Topology:
    nodes: dict = field(default_factory=dict)      # node -> {"tier", "site", "caps"}
    links: dict = field(default_factory=dict)      # frozenset({a,b}) -> (latency_ms, up)

    def add(self, node, tier, site, caps=()):
        self.nodes[node] = {"tier": tier, "site": site, "caps": frozenset(caps)}

    def connect(self, a, b, latency, up=True):
        self.links[frozenset((a, b))] = (latency, up)

    def _neighbours(self, n):
        for pair, (lat, up) in self.links.items():
            if n in pair and up:
                (other,) = pair - {n}
                yield other, lat

    def nearest(self, origin, cap):
        seen, heap = set(), [(0, origin)]
        while heap:
            dist, n = heapq.heappop(heap)
            if n in seen:
                continue
            seen.add(n)
            if cap in self.nodes[n]["caps"]:
                return n, dist
            for m, lat in self._neighbours(n):
                if m not in seen:
                    heapq.heappush(heap, (dist + lat, m))
        return None, None

    def partitioned(self, site, cloud="cloud"):
        members = [n for n, v in self.nodes.items() if v["site"] == site]
        return all(self.nearest(m, "control")[0] in (None,) or
                   self.nodes[self.nearest(m, "control")[0]]["site"] == site for m in members)

    def elect(self, site):
        """Deterministic: lowest node name among the site's members wins."""
        return min(n for n, v in self.nodes.items() if v["site"] == site)


class EdgeTopologyComponent(Component):
    """Master-applied component for INV-62."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _estate(self):
        t = Topology()
        t.add("cloud", "cloud", "cloud", ["control", "gpu"])
        t.add("s1-gw", "site", "s1", ["cache"])
        t.add("s1-d1", "device", "s1", [])
        t.add("s1-d2", "device", "s1", ["gpu"])
        t.connect("cloud", "s1-gw", 80)
        t.connect("s1-gw", "s1-d1", 2)
        t.connect("s1-gw", "s1-d2", 3)
        return t

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        t = self._estate()
        node, ms = t.nearest("s1-d1", "gpu")
        assert (node, ms) == ("s1-d2", 5)
        findings[0] = self.satisfied(
            items[0],
            "Resolution picks the nearest capable node by measured latency: a GPU request from a device "
            "resolves to the GPU box on the same site (5 ms) rather than the cloud (82 ms).",
            *self._evidence("component.py::Topology.nearest"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        t = self._estate()
        assert not t.partitioned("s1")
        t.connect("cloud", "s1-gw", 80, up=False)
        node, _ = t.nearest("s1-d1", "control")
        assert node is None and t.partitioned("s1") and t.elect("s1") == "s1-d1"
        assert t.nearest("s1-d1", "gpu")[0] == "s1-d2"
        findings[0] = self.satisfied(
            items[0],
            "When the uplink goes down no route crosses it, the site is recognised as partitioned, a "
            "local coordinator is elected deterministically, and on-site capabilities keep resolving.",
            *self._evidence("component.py::Topology.partitioned", "component.py::Topology.elect"))
        return findings

COMPONENT = EdgeTopologyComponent
