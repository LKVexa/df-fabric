"""GAP-03 - Topology-aware scheduler.

The topology-aware scheduler supplies what a flat scheduler cannot: locality cost and fair share. It scores candidates by how far they are from the data and the caller, and it refuses to let one tenant's demand crowd out another's floor.

The component answers all 100 requirements of the GAP-03 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Cost added per level climbed in the topology tree.
LEVEL_COST = {"rack": 1, "site": 10, "region": 100}


class NotInTopology(KeyError):
    """Raised when a candidate node is not present in the declared topology graph."""


class ShareViolation(PermissionError):
    """Raised when a placement would spend capacity reserved for another tenant."""


@dataclass
class Topology:
    """A region/site/rack tree. Distance is the cost of climbing to a common ancestor."""

    #: node -> (region, site, rack)
    nodes: dict = field(default_factory=dict)

    def place(self, node: str, region: str, site: str, rack: str) -> None:
        self.nodes[node] = (region, site, rack)

    def path(self, node: str) -> tuple:
        if node not in self.nodes:
            raise NotInTopology(f"{node} is not in the declared topology")
        return self.nodes[node]

    def cost(self, a: str, b: str) -> int:
        """Deterministic locality cost; zero for the same node."""
        if a == b:
            return 0
        ra, sa, ka = self.path(a)
        rb, sb, kb = self.path(b)
        if ra != rb:
            return LEVEL_COST["region"]
        if sa != sb:
            return LEVEL_COST["site"]
        if ka != kb:
            return LEVEL_COST["rack"]
        return 1

    def domain(self, node: str) -> str:
        region, site, _ = self.path(node)
        return f"{region}/{site}"


@dataclass
class FairShare:
    """Reserved shares per tenant, enforced before surplus demand is served."""

    reserved: dict = field(default_factory=dict)   # tenant -> reserved slots
    used: dict = field(default_factory=dict)       # tenant -> slots currently held
    capacity: int = 0

    def held(self, tenant: str) -> int:
        return self.used.get(tenant, 0)

    def starved(self) -> list:
        return sorted(t for t, r in self.reserved.items() if self.held(t) < r)

    def surplus(self) -> int:
        """Capacity beyond every tenant's unmet reservation."""
        unmet = sum(max(0, r - self.held(t)) for t, r in self.reserved.items())
        return self.capacity - sum(self.used.values()) - unmet

    def claim(self, tenant: str, slots: int = 1) -> None:
        """Claim slots, refusing anything that would eat another tenant's reservation."""
        within_own = max(0, self.reserved.get(tenant, 0) - self.held(tenant))
        beyond = slots - within_own
        if beyond > 0 and beyond > self.surplus():
            raise ShareViolation(
                f"{tenant}: claiming {slots} slot(s) would spend reserved capacity "
                f"(own headroom {within_own}, surplus {self.surplus()})")
        self.used[tenant] = self.held(tenant) + slots


def rank(topology: Topology, anchor: str, candidates: list, *, spread_from=()) -> list:
    """Rank candidates by locality cost to ``anchor``, penalising shared failure domains."""
    taken = {topology.domain(n) for n in spread_from}
    scored = []
    for node in candidates:
        cost = topology.cost(anchor, node)
        penalty = LEVEL_COST["region"] if topology.domain(node) in taken else 0
        scored.append((cost + penalty, node))
    return [node for _, node in sorted(scored)]


class TopologyAwareSchedulerComponent(Component):
    """Master-applied component for GAP-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "dub", "r2")
        topo.place("c", "eu", "ams", "r1")
        topo.place("d", "us", "iad", "r1")
        assert topo.cost("a", "a") == 0 < topo.cost("a", "b") < topo.cost("a", "c") < topo.cost("a", "d")
        order = rank(topo, "a", ["d", "c", "b"])
        assert order == ["b", "c", "d"], f"ranking is not locality-ordered: {order}"
        assert rank(topo, "a", ["d", "c", "b"]) == order, "ranking is not deterministic"
        findings[5] = self.satisfied(
            items[5],
            f"Locality cost is monotone across rack/site/region and ranking is deterministic: {order}.",
            *self._evidence("component.py::Topology.cost", "component.py::rank"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[1] = self.satisfied(
            items[1],
            "This element supplies cost and a fairness verdict only; SCH-01 keeps the placement decision, "
            "so hard-constraint filtering is never traded away for a better locality score.",
            *self._evidence("contract.py", "component.py::rank"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        try:
            topo.cost("a", "rogue")
        except NotInTopology:
            findings[6] = self.satisfied(
                items[6],
                "A node absent from the declared topology cannot be scored, so a forged node cannot pull "
                "work toward itself.",
                *self._evidence("component.py::Topology.path"))
        share = FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
        share.claim("t1", 4)
        try:
            share.claim("t1", 4)
        except ShareViolation:
            findings[5] = self.satisfied(
                items[5],
                "A tenant past its own reservation cannot claim capacity reserved for another tenant.",
                *self._evidence("component.py::FairShare.claim"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        share = FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
        share.claim("t1", 4)
        assert share.starved() == ["t2"], "starvation went undetected"
        share.claim("t2", 4)
        assert share.starved() == []
        findings[7] = self.satisfied(
            items[7],
            "Starvation is detected as a first-class state: a tenant below its reservation is reported "
            "before its demand is served.",
            *self._evidence("component.py::FairShare.starved"))
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "ams", "r1")
        topo.place("c", "eu", "dub", "r2")
        spread = rank(topo, "a", ["c", "b"], spread_from=["a"])
        assert spread[0] == "b", "anti-affinity did not penalise the shared failure domain"
        findings[6] = self.satisfied(
            items[6],
            "Anti-affinity penalises candidates sharing a failure domain with the existing group, "
            "bounding blast radius across sites.",
            *self._evidence("component.py::rank"))
        return findings

COMPONENT = TopologyAwareSchedulerComponent
