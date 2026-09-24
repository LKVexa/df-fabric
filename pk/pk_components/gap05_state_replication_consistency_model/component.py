"""GAP-05 - State replication/consistency model.

The state replication and consistency model makes the edge's divergence explicit. Writes taken on both sides of a partition are kept, not silently lost: the model merges what commutes, and surfaces what genuinely conflicts for a decision instead of picking a winner by timestamp.

The component answers all 100 requirements of the GAP-05 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class UnknownReplica(KeyError):
    """Raised when a version vector references a site that is not a declared replica."""


@dataclass(frozen=True)
class Write:
    """One write, stamped with the causal context its author had seen."""

    key: str
    value: str
    site: str
    vector: tuple            # ((site, counter), ...) sorted; the author's causal context

    def vector_map(self) -> dict:
        return dict(self.vector)


def dominates(a: dict, b: dict) -> bool:
    """True when vector ``a`` causally succeeds ``b`` (a >= b everywhere, and strictly greater somewhere)."""
    sites = set(a) | set(b)
    ge = all(a.get(s, 0) >= b.get(s, 0) for s in sites)
    gt = any(a.get(s, 0) > b.get(s, 0) for s in sites)
    return ge and gt


def concurrent(a: dict, b: dict) -> bool:
    """True when neither vector dominates the other and they are not equal."""
    return a != b and not dominates(a, b) and not dominates(b, a)


@dataclass
class ReplicatedKey:
    """One replicated key: converges on causality, keeps genuine conflicts open."""

    key: str
    replicas: frozenset
    #: Surviving writes -- one when converged, several when in conflict.
    siblings: list = field(default_factory=list)
    discarded: list = field(default_factory=list)
    #: Hard bound on open siblings.  Shedding policy: a write that would exceed it is
    #: refused and quarantined with its reason -- never silently dropped, never allowed
    #: to evict an existing sibling -- until an operator resolves the open conflict.
    max_siblings: int = 8
    quarantine: list = field(default_factory=list)

    def apply(self, write: Write) -> str:
        """Apply a write. Returns 'converged', 'conflict', 'duplicate', or 'superseded'."""
        unknown = set(write.vector_map()) - set(self.replicas)
        if unknown or write.site not in self.replicas:
            raise UnknownReplica(f"{self.key}: vector references non-replica {sorted(unknown) or write.site}")

        incoming = write.vector_map()
        for sibling in self.siblings:
            if sibling.vector_map() == incoming and sibling.value == write.value:
                self.discarded.append({"write": write, "reason": "duplicate: already applied"})
                return "duplicate"

        survivors, superseded = [], []
        for sibling in self.siblings:
            existing = sibling.vector_map()
            if dominates(existing, incoming):
                # The incoming write is causally older; keep the sibling, record the drop.
                self.discarded.append({"write": write, "reason": f"superseded by {sibling.site}"})
                return "superseded"
            if dominates(incoming, existing):
                superseded.append(sibling)
            else:
                survivors.append(sibling)
        for sibling in superseded:
            self.discarded.append({"write": sibling, "reason": f"superseded by {write.site}"})

        if len(survivors) + 1 > self.max_siblings:
            self.quarantine.append({"write": write,
                                    "reason": f"conflict set full ({self.max_siblings} open siblings)"})
            return "quarantined"
        survivors.append(write)
        # Deterministic sibling order so convergence does not depend on delivery order.
        self.siblings = sorted(survivors, key=lambda w: (w.site, w.value, w.vector))
        return "conflict" if len(self.siblings) > 1 else "converged"

    @property
    def converged(self) -> bool:
        return len(self.siblings) <= 1

    def value(self):
        if not self.converged:
            raise ValueError(f"{self.key}: {len(self.siblings)} concurrent siblings await resolution")
        return self.siblings[0].value if self.siblings else None

    def conflict_set(self) -> dict:
        return {"schema": "PK_CONFLICT_SET/1", "key": self.key,
                "siblings": [{"site": w.site, "value": w.value, "vector": list(w.vector)}
                             for w in self.siblings],
                "open": not self.converged}

    def resolve(self, value: str, site: str) -> Write:
        """Resolve a conflict by writing a value that causally dominates every sibling."""
        merged = {}
        for sibling in self.siblings:
            for s, c in sibling.vector_map().items():
                merged[s] = max(merged.get(s, 0), c)
        merged[site] = merged.get(site, 0) + 1
        winner = Write(self.key, value, site, tuple(sorted(merged.items())))
        for sibling in self.siblings:
            self.discarded.append({"write": sibling, "reason": f"resolved by {site}"})
        self.siblings = [winner]
        return winner


class StateReplicationConsistencyModelComponent(Component):
    """Master-applied component for GAP-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        replicas = frozenset({"dub", "ams"})
        w1 = Write("k", "v1", "dub", (("dub", 1),))
        w2 = Write("k", "v2", "ams", (("ams", 1),))
        w3 = Write("k", "v3", "dub", (("ams", 1), ("dub", 2)))

        forward = ReplicatedKey("k", replicas)
        for w in (w1, w2, w3):
            forward.apply(w)
        backward = ReplicatedKey("k", replicas)
        for w in (w3, w2, w1):
            backward.apply(w)
        assert [s.value for s in forward.siblings] == [s.value for s in backward.siblings], \
            "convergence depends on delivery order"
        findings[5] = self.satisfied(
            items[5],
            f"Convergence is order-independent: forward and reverse delivery both settle on "
            f"{[s.value for s in forward.siblings]}.",
            *self._evidence("component.py::ReplicatedKey.apply"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        replicas = frozenset({"dub", "ams"})
        key = ReplicatedKey("k", replicas)
        assert key.apply(Write("k", "v1", "dub", (("dub", 1),))) == "converged"
        assert key.apply(Write("k", "v2", "ams", (("ams", 1),))) == "conflict"
        assert not key.converged and len(key.siblings) == 2
        findings[4] = self.satisfied(
            items[4],
            "Causally concurrent writes become a two-sibling conflict rather than a last-writer-wins "
            "resolution; both values survive until something decides.",
            *self._evidence("component.py::concurrent", "component.py::ReplicatedKey.apply"))
        winner = key.resolve("merged", "dub")
        assert key.converged and key.value() == "merged" and len(key.discarded) == 2
        findings[3] = self.satisfied(
            items[3],
            f"Resolution writes a value dominating every sibling ({list(winner.vector)}) and records both "
            "discarded siblings with their reason.",
            *self._evidence("component.py::ReplicatedKey.resolve"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        key = ReplicatedKey("k", frozenset({"dub"}))
        try:
            key.apply(Write("k", "v", "rogue", (("rogue", 99),)))
        except UnknownReplica:
            findings[3] = self.satisfied(
                items[3],
                "A write whose vector names a site that is not a declared replica is refused, so a forged "
                "vector cannot win a merge.",
                *self._evidence("component.py::ReplicatedKey.apply"))
        findings[6] = self.satisfied(
            items[6],
            "Ordering is causal only: no code path consults wall-clock time, so clock manipulation cannot "
            "reorder a hostile write to the front.",
            *self._evidence("component.py::dominates"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        replicas = frozenset({"dub", "ams"})
        key = ReplicatedKey("k", replicas)
        w = Write("k", "v1", "dub", (("dub", 1),))
        key.apply(w)
        assert key.apply(w) == "duplicate", "replay was applied twice"
        assert key.discarded[-1]["reason"].startswith("duplicate")
        findings[4] = self.satisfied(
            items[4],
            "Write application is idempotent: a replayed write is recorded as a discard with its reason "
            "rather than re-applied.",
            *self._evidence("component.py::ReplicatedKey.apply"))
        findings[8] = self.satisfied(
            items[8],
            f"Every discard carries a reason ({len(key.discarded)} recorded), so no write disappears "
            "without a trace.",
            *self._evidence("component.py::ReplicatedKey.discarded"))
        sites = frozenset(f"s{i}" for i in range(6))
        bounded = ReplicatedKey("cart", sites, max_siblings=3)
        outcomes = [bounded.apply(Write("cart", f"v{i}", f"s{i}", ((f"s{i}", 1),))) for i in range(5)]
        assert outcomes == ["converged", "conflict", "conflict", "quarantined", "quarantined"]
        assert len(bounded.siblings) == 3 and len(bounded.quarantine) == 2
        bounded.resolve("merged", "s0")
        assert bounded.apply(Write("cart", "late", "s5", (("s5", 1),))) == "conflict"
        findings[2] = self.satisfied(
            items[2],
            "The conflict set is bounded (3 open siblings here) with a documented shedding policy: "
            "writes past the bound are refused into a quarantine with their reason rather than dropped "
            "or allowed to evict an existing sibling, and once the conflict is resolved new concurrent "
            "writes are accepted again.",
            *self._evidence("component.py::ReplicatedKey.apply", "component.py::ReplicatedKey.quarantine"))
        return findings

COMPONENT = StateReplicationConsistencyModelComponent
