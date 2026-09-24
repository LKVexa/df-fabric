"""INV-04 - Current orchestration.

Current orchestration is the scheduler the estate uses today: desired replica counts, reconciliation, and node drains for maintenance. The new platform has to coexist with it and eventually take over, so its behaviour is modelled exactly -- including the rule that a drain must never take a service below its disruption budget.

The component answers all 100 requirements of the INV-04 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class BudgetBreach(RuntimeError):
    pass


@dataclass
class Cluster:
    nodes: list
    pods: list = field(default_factory=list)          # [(workload, node)]
    desired: dict = field(default_factory=dict)
    min_available: dict = field(default_factory=dict)

    def reconcile(self) -> int:
        changes = 0
        for w, n in self.desired.items():
            running = [p for p in self.pods if p[0] == w]
            for _ in range(n - len(running)):
                load = {nd: sum(1 for p in self.pods if p[1] == nd) for nd in self.nodes}
                self.pods.append((w, min(self.nodes, key=lambda nd: (load[nd], nd))))
                changes += 1
            for p in running[n:]:
                self.pods.remove(p)
                changes += 1
        return changes

    def drain(self, node: str) -> int:
        victims = [p for p in self.pods if p[1] == node]
        for w in {p[0] for p in victims}:
            remaining = sum(1 for p in self.pods if p[0] == w and p[1] != node)
            if remaining < self.min_available.get(w, 0):
                raise BudgetBreach(f"draining {node} leaves {w} with {remaining} < {self.min_available[w]}")
        self.nodes.remove(node)
        for p in victims:
            self.pods.remove(p)
        return self.reconcile()


class CurrentOrchestrationComponent(Component):
    """Master-applied component for INV-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        c = Cluster(["n1", "n2", "n3"], desired={"api": 3}, min_available={"api": 2})
        c.reconcile()
        moved = c.drain("n1")
        assert moved == 1 and len([p for p in c.pods if p[0] == "api"]) == 3
        blocked = False
        tight = Cluster(["n1", "n2"], desired={"db": 2}, min_available={"db": 2})
        tight.reconcile()
        try:
            tight.drain("n1")
        except BudgetBreach:
            blocked = True
        assert blocked and "n1" in tight.nodes
        findings[0] = self.satisfied(
            items[0],
            "A drain that keeps the service within its budget proceeds and the evicted replica is "
            "rescheduled (still 3 running); a drain that would drop a service below its minimum is "
            "refused before anything is evicted.",
            *self._evidence("component.py::Cluster.drain"))
        return findings

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = Cluster(["a", "b"], desired={"web": 4})
        c.reconcile()
        c.pods.pop()
        c.desired["web"] = 2
        c.reconcile()
        assert len(c.pods) == 2 and c.reconcile() == 0
        findings[0] = self.satisfied(
            items[0],
            "Running replicas are corrected toward the desired count in both directions -- a lost pod "
            "is replaced, a scale-down removes extras -- and a converged cluster makes no further changes.",
            *self._evidence("component.py::Cluster.reconcile"))
        return findings

COMPONENT = CurrentOrchestrationComponent
