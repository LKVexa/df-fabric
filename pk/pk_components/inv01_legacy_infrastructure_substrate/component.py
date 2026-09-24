"""INV-01 - Legacy infrastructure substrate.

The legacy infrastructure substrate is everything that already runs: physical hosts and long-lived VMs, many past vendor support, some with nobody clearly responsible for them. Moving to a new platform starts with an honest inventory. This element compares what the records say with what was actually discovered, tracks end-of-life dates, and refuses to schedule a host for migration until every workload on it has an owner.

The component answers all 100 requirements of the INV-01 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


@dataclass
class LegacyInventory:
    recorded: dict                                  # host -> {"eol": year}
    discovered: dict                                # host -> [workloads]
    owners: dict = field(default_factory=dict)      # workload -> owner

    def reconcile(self) -> dict:
        rec, disc = set(self.recorded), set(self.discovered)
        return {"matched": sorted(rec & disc), "ghosts": sorted(rec - disc), "strays": sorted(disc - rec)}

    def end_of_life(self, year: int) -> list:
        return sorted(h for h, v in self.recorded.items() if v.get("eol", 9999) <= year and h in self.discovered)

    def eligible(self, host: str) -> dict:
        if host not in self.discovered:
            return {"host": host, "eligible": False, "reasons": ["host not discovered"]}
        reasons = [f"workload {w} has no owner" for w in self.discovered[host] if not self.owners.get(w)]
        if host not in self.recorded:
            reasons.append("host is a stray with no record")
        return {"host": host, "eligible": not reasons, "reasons": reasons}


class LegacyInfrastructureSubstrateComponent(Component):
    """Master-applied component for INV-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _estate(self):
        return LegacyInventory(
            recorded={"db-01": {"eol": 2024}, "app-01": {"eol": 2029}, "old-07": {"eol": 2019}},
            discovered={"db-01": ["billing-db"], "app-01": ["portal", "cron-x"], "rogue-3": ["?"]},
            owners={"billing-db": "finance-eng", "portal": "web"})

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        inv = self._estate()
        r = inv.reconcile()
        assert r == {"matched": ["app-01", "db-01"], "ghosts": ["old-07"], "strays": ["rogue-3"]}
        assert inv.end_of_life(2026) == ["db-01"]
        findings[0] = self.satisfied(
            items[0],
            "Discovery is reconciled against the records: a recorded host that no longer answers is "
            "reported as a ghost, an unrecorded host that does answer as a stray, and a live host past "
            "end of life (db-01, 2024) is flagged.",
            *self._evidence("component.py::LegacyInventory.reconcile", "component.py::LegacyInventory.end_of_life"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        inv = self._estate()
        ok, blocked, stray = inv.eligible("db-01"), inv.eligible("app-01"), inv.eligible("rogue-3")
        assert ok["eligible"] and not blocked["eligible"] and "cron-x" in blocked["reasons"][0]
        assert not stray["eligible"]
        findings[0] = self.satisfied(
            items[0],
            "Migration eligibility is refused while any workload on the host lacks an owner (app-01 is "
            "held for cron-x), and a stray host cannot move until it is recorded.",
            *self._evidence("component.py::LegacyInventory.eligible"))
        return findings

COMPONENT = LegacyInfrastructureSubstrateComponent
