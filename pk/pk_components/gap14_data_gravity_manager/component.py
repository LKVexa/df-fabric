"""GAP-14 - Data-gravity manager.

The data-gravity manager decides whether the computation moves to the data or the data moves to the computation. It costs both directions honestly against residency and egress, and it will recommend neither rather than propose a move that residency forbids.

The component answers all 100 requirements of the GAP-14 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Cost per gigabyte of egress, and the fixed cost of relocating a compute workload.
EGRESS_PER_GB = 1.0
COMPUTE_MOVE_COST = 25.0


class NoLegalOption(RuntimeError):
    """Raised when residency forbids every way of bringing data and compute together."""


@dataclass(frozen=True)
class Dataset:
    name: str
    site: str
    size_gb: float
    classification: str
    converged: bool = True


@dataclass
class GravityManager:
    """Decides whether compute moves to the data or the data moves to the compute."""

    #: site -> set of classifications it may legally hold
    residency: dict = field(default_factory=dict)
    #: (from_site, to_site) -> locality multiplier
    distance: dict = field(default_factory=dict)
    #: sites where compute can actually run
    compute_sites: frozenset = frozenset()

    def legal(self, site: str, classification: str) -> bool:
        return classification in self.residency.get(site, set())

    def move_data_cost(self, dataset: Dataset, to_site: str) -> float:
        multiplier = self.distance.get((dataset.site, to_site), 1.0)
        return dataset.size_gb * EGRESS_PER_GB * multiplier

    def move_compute_cost(self, from_site: str, to_site: str) -> float:
        multiplier = self.distance.get((from_site, to_site), 1.0)
        return COMPUTE_MOVE_COST * multiplier

    def recommend(self, dataset: Dataset, compute_site: str) -> dict:
        """Cost both directions; residency filters first, cost decides second."""
        if compute_site == dataset.site:
            return {"schema": "PK_GRAVITY_RECOMMENDATION/1", "direction": "none",
                    "reason": "compute and data are already co-located", "cost": 0.0,
                    "options": []}

        options, eliminated = [], []

        # Option A: move the compute to the data's site.
        if not self.legal(dataset.site, dataset.classification):
            eliminated.append(f"move-compute: {dataset.site} may not hold {dataset.classification}")
        elif dataset.site not in self.compute_sites:
            eliminated.append(f"move-compute: no compute capacity at {dataset.site}")
        else:
            options.append({"direction": "move-compute", "to": dataset.site,
                            "cost": self.move_compute_cost(compute_site, dataset.site)})

        # Option B: move the data to the compute's site.
        if not self.legal(compute_site, dataset.classification):
            eliminated.append(f"move-data: {compute_site} may not hold {dataset.classification}")
        elif not dataset.converged:
            eliminated.append(f"move-data: {dataset.name} has unresolved replication conflicts")
        else:
            options.append({"direction": "move-data", "to": compute_site,
                            "cost": self.move_data_cost(dataset, compute_site)})

        if not options:
            raise NoLegalOption(
                f"{dataset.name}: no legal way to co-locate with compute at {compute_site} "
                f"({'; '.join(eliminated)})")

        best = min(options, key=lambda o: (o["cost"], o["direction"]))
        return {"schema": "PK_GRAVITY_RECOMMENDATION/1", "direction": best["direction"],
                "to": best["to"], "cost": best["cost"],
                "reason": f"cheapest legal option at {best['cost']:.1f}",
                "options": sorted(options, key=lambda o: o["direction"]),
                "eliminated": eliminated}


class DataGravityManagerComponent(Component):
    """Master-applied component for GAP-14."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        g = GravityManager(residency={"dub": {"public"}, "ams": {"public"}},
                           distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
                           compute_sites=frozenset({"dub", "ams"}))
        big = Dataset("lake", "dub", size_gb=500, classification="public")
        small = Dataset("lookup", "dub", size_gb=2, classification="public")
        assert g.recommend(big, "ams")["direction"] == "move-compute"
        assert g.recommend(small, "ams")["direction"] == "move-data"
        findings[5] = self.satisfied(
            items[5],
            "The cost model inverts at the expected scale: a 500GB dataset pulls the compute to it, a 2GB "
            "dataset moves to the compute.",
            *self._evidence("component.py::GravityManager.recommend"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        g = GravityManager(residency={"dub": {"pii", "public"}, "ams": {"public"}},
                           distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
                           compute_sites=frozenset({"dub", "ams"}))
        pii = Dataset("customers", "dub", size_gb=1, classification="pii")
        result = g.recommend(pii, "ams")
        assert result["direction"] == "move-compute", "cheap illegal move-data was chosen"
        assert any("may not hold pii" in e for e in result["eliminated"])
        findings[5] = self.satisfied(
            items[5],
            "A 1GB PII dataset is not moved to a non-PII site even though moving it is far cheaper: "
            "residency eliminates the option before cost is compared.",
            *self._evidence("component.py::GravityManager.recommend"))
        pinned = GravityManager(residency={"dub": {"pii"}, "ams": {"public"}},
                                compute_sites=frozenset({"ams"}))
        try:
            pinned.recommend(Dataset("pinned", "dub", 1, "pii"), "ams")
        except NoLegalOption:
            findings[8] = self.satisfied(
                items[8],
                "When residency forbids both directions the answer is a refusal, not the least-bad move.",
                *self._evidence("component.py::GravityManager.recommend"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        g = GravityManager(residency={"dub": {"public"}, "ams": {"public"}},
                           compute_sites=frozenset({"ams"}))
        unconverged = Dataset("live", "dub", size_gb=1, classification="public", converged=False)
        try:
            g.recommend(unconverged, "ams")
        except NoLegalOption as exc:
            assert "unresolved replication conflicts" in str(exc)
            findings[3] = self.satisfied(
                items[3],
                "A dataset with open replication conflicts is not moved; GAP-05 convergence is a "
                "precondition, so a move cannot silently pick a conflict winner.",
                *self._evidence("component.py::GravityManager.recommend"))
        same = g.recommend(Dataset("d", "ams", 1, "public"), "ams")
        assert same["direction"] == "none" and same["cost"] == 0.0
        findings[4] = self.satisfied(
            items[4],
            "Recommending a move for already co-located data is a no-op rather than a wasted transfer, so "
            "repeated calls are idempotent.",
            *self._evidence("component.py::GravityManager.recommend"))
        return findings

COMPONENT = DataGravityManagerComponent
