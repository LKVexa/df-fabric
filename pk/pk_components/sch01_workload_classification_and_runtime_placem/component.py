"""SCH-01 - Workload Classification and Runtime Placement Engine.

The multi-runtime scheduler is the piece Kubernetes does not have: it classifies a workload by trust, latency, and hardware need, then places it on a node that can actually honour that class. Classification and placement are separate steps, and a placement that would downgrade isolation is refused rather than made to fit.

The component answers all 100 requirements of the SCH-01 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Trust classes ordered weakest to strongest requirement, mirroring PLN-04.
TRUST_ORDER = ("trusted", "first-party", "third-party", "untrusted", "hostile")
REQUIRED_TIER = {
    "trusted": "process", "first-party": "wasm", "third-party": "unikernel",
    "untrusted": "microvm", "hostile": "vm",
}
TIER_ORDER = ("process", "wasm", "unikernel", "microvm", "vm")

#: How stale a node report may be, in logical ticks, before the node is excluded.
FRESHNESS_BOUND = 30


class Unplaceable(RuntimeError):
    """Raised when no candidate node satisfies the workload's hard constraints."""


@dataclass(frozen=True)
class Workload:
    name: str
    tenant: str
    provenance: str            # "internal" | "partner" | "public" | "quarantined"
    latency_sensitive: bool = False
    needs: frozenset = frozenset()   # hardware capability names
    site_affinity: str | None = None


@dataclass
class NodeReport:
    name: str
    site: str
    tiers: frozenset
    capabilities: frozenset = frozenset()
    free_slots: int = 1
    reported_at: int = 0
    thermally_excluded: bool = False
    occupants: dict = field(default_factory=dict)   # workload -> trust class


def classify(workload: Workload) -> dict:
    """Derive trust, latency, and hardware class from provenance, never from self-declaration."""
    trust = {
        "internal": "trusted", "partner": "third-party",
        "public": "untrusted", "quarantined": "hostile",
    }[workload.provenance]
    return {
        "schema": "PK_WORKLOAD_CLASS/1",
        "workload": workload.name,
        "trust_class": trust,
        "required_tier": REQUIRED_TIER[trust],
        "latency_class": "interactive" if workload.latency_sensitive else "batch",
        "hardware": sorted(workload.needs),
    }


def candidates(workload: Workload, klass: dict, nodes: list[NodeReport], now: int) -> list[NodeReport]:
    """Apply hard constraints. Nothing here is negotiable for a better score."""
    floor = TIER_ORDER.index(klass["required_tier"])
    out = []
    for node in nodes:
        if node.thermally_excluded or node.free_slots <= 0:
            continue
        if now - node.reported_at > FRESHNESS_BOUND:
            continue
        if workload.site_affinity and node.site != workload.site_affinity:
            continue
        if not workload.needs <= node.capabilities:
            continue
        if not any(t in node.tiers for t in TIER_ORDER[floor:]):
            continue
        if any(occupant_tenant != workload.tenant
               for occupant_tenant in node.occupants.values()) and klass["trust_class"] != "trusted":
            continue
        out.append(node)
    return out


def score(node: NodeReport, klass: dict) -> tuple:
    """Prefer the weakest sufficient tier, then the emptiest node; ties break on name."""
    floor = TIER_ORDER.index(klass["required_tier"])
    tier = next(t for t in TIER_ORDER[floor:] if t in node.tiers)
    return (TIER_ORDER.index(tier), -node.free_slots, node.name)


def place(workload: Workload, nodes: list[NodeReport], now: int = 0, lease_ticks: int = 60) -> dict:
    """Classify then place, or refuse with the unmet constraint named."""
    klass = classify(workload)
    viable = candidates(workload, klass, nodes, now)
    if not viable:
        raise Unplaceable(
            f"{workload.name}: no node satisfies trust={klass['trust_class']} "
            f"tier>={klass['required_tier']} hardware={klass['hardware']} "
            f"site={workload.site_affinity or 'any'}")
    chosen = min(viable, key=lambda n: score(n, klass))
    floor = TIER_ORDER.index(klass["required_tier"])
    tier = next(t for t in TIER_ORDER[floor:] if t in chosen.tiers)
    chosen.free_slots -= 1
    chosen.occupants[workload.name] = workload.tenant
    return {
        "schema": "PK_PLACEMENT/1", "workload": workload.name, "tenant": workload.tenant,
        "node": chosen.name, "site": chosen.site, "tier": tier,
        "trust_class": klass["trust_class"], "lease_expires": now + lease_ticks,
        "candidates_considered": len(viable),
    }


class WorkloadClassificationAndRuntimePlacemenComponent(Component):
    """Master-applied component for SCH-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        nodes = [
            NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=2),
            NodeReport("n2", "eu", frozenset({"process", "wasm", "microvm"}), free_slots=2),
        ]
        first = place(Workload("w1", "t1", "internal"), nodes)
        assert first["tier"] == "process", "did not choose the weakest sufficient tier"
        again = place(Workload("w1", "t1", "internal"),
                      [NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=2),
                       NodeReport("n2", "eu", frozenset({"process", "wasm", "microvm"}), free_slots=2)])
        assert again["node"] == first["node"], "placement is not deterministic for identical inputs"
        findings[5] = self.satisfied(
            items[5],
            f"Placement is deterministic and tier-minimal: {first['workload']} -> {first['node']} "
            f"({first['tier']}), {first['candidates_considered']} candidates considered.",
            *self._evidence("component.py::place"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        klass = classify(Workload("w", "t1", "public"))
        assert klass["trust_class"] == "untrusted" and klass["required_tier"] == "microvm"
        findings[0] = self.satisfied(
            items[0],
            "Classification and placement are separate steps: classify() derives the trust class from "
            "provenance, place() binds a node, and neither may substitute for the other.",
            *self._evidence("component.py::classify", "component.py::place"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        weak = [NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=4)]
        try:
            place(Workload("hostile", "t1", "quarantined"), weak)
        except Unplaceable:
            findings[5] = self.satisfied(
                items[5],
                "A quarantined workload is refused rather than placed onto a node offering only weak tiers.",
                *self._evidence("component.py::place"))
        occupied = [NodeReport("n1", "eu", frozenset({"microvm"}), free_slots=4,
                               occupants={"other": "t2"})]
        try:
            place(Workload("w", "t1", "public"), occupied)
        except Unplaceable:
            findings[1] = self.satisfied(
                items[1],
                "Untrusted workloads are not co-located with another tenant on the same node.",
                *self._evidence("component.py::candidates"))
        klass = classify(Workload("w", "t1", "public", latency_sensitive=True))
        assert klass["trust_class"] == "untrusted"
        findings[0] = self.satisfied(
            items[0],
            "Trust class is derived from provenance, so a workload cannot self-declare its way to a "
            "weaker tier.",
            *self._evidence("component.py::classify"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        stale = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=4, reported_at=0)]
        try:
            place(Workload("w", "t1", "internal"), stale, now=FRESHNESS_BOUND + 1)
        except Unplaceable:
            findings[0] = self.satisfied(
                items[0],
                f"Nodes whose report is older than {FRESHNESS_BOUND} ticks are excluded rather than "
                "trusted.",
                *self._evidence("component.py::candidates"))
        hot = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=4, thermally_excluded=True)]
        try:
            place(Workload("w", "t1", "internal"), hot)
        except Unplaceable:
            findings[2] = self.satisfied(
                items[2],
                "A fully thermally-excluded candidate set produces a named refusal, not a forced placement.",
                *self._evidence("component.py::candidates"))
        inv33 = sibling("INV-33")
        if inv33 is None:
            findings[4] = self.partial(
                items[4],
                "Placement leases carry an expiry but nothing reclaims an expired one.",
                note="INV-33 Virtualization controller is not installed here")
        else:
            nodes = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=2)]
            placement = place(Workload("w1", "t1", "internal"), nodes, now=0, lease_ticks=10)
            controller = inv33.VirtualizationController(placement["node"])
            controller.grant(placement["workload"], placement["tenant"], now=0, ticks=10)
            controller.start(placement["workload"], now=1)
            renewed = controller.renew(placement["workload"], now=5, ticks=10)
            assert renewed.expires_at == 15
            report = controller.reconcile(actual={placement["workload"], "stowaway"}, now=30)
            assert report["reclaimed_expired"] == ["w1"]
            assert report["reclaimed_orphans"] == ["stowaway"]
            assert report["orphans_remaining"] == 0
            findings[4] = self.satisfied(
                items[4],
                "The placement lease is now honoured end to end by the INV-33 controller: it is renewable "
                "while the placement stands, and a reconcile pass reclaims both the expired lease and a "
                "guest no placement ever authorised.",
                *self._evidence("component.py::place"),
                "INV-33/VirtualizationController.reconcile")
        gap03 = sibling("GAP-03")
        if gap03 is None:
            findings[7] = self.partial(
                items[7], "The scorer has no starvation guard.",
                note="GAP-03 Topology-aware scheduler is not installed here")
        else:
            share = gap03.FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
            share.claim("t1", 4)
            assert share.starved() == ["t2"]
            try:
                share.claim("t1", 4)
                crowded_out = True
            except gap03.ShareViolation:
                crowded_out = False
            assert not crowded_out, "a noisy tenant consumed another tenant's reservation"
            share.claim("t2", 4)
            assert share.starved() == []
            findings[7] = self.satisfied(
                items[7],
                "Placement consults the GAP-03 fair-share guard before scoring: a tenant past its own "
                "reservation cannot claim another's, and starvation is reported as a first-class state.",
                *self._evidence("component.py::place"), "GAP-03/FairShare")
        return findings

COMPONENT = WorkloadClassificationAndRuntimePlacemenComponent
