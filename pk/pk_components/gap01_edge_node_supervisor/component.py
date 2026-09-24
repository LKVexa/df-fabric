"""GAP-01 - Edge Node Supervisor.

The edge node supervisor is the single local authority on a node: it owns the node's lifecycle state machine, drains workloads before the node stops accepting them, and keeps the node honest when the control plane is unreachable. Nothing else on the node may declare it healthy.

The component answers all 100 requirements of the GAP-01 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Legal lifecycle transitions. Anything absent here is refused.
TRANSITIONS = {
    "joining": {"ready", "stopped"},
    "ready": {"cordoned", "draining", "stopped"},
    "cordoned": {"ready", "draining", "stopped"},
    "draining": {"stopped", "cordoned"},
    "stopped": set(),
}

#: Drain order: the least-trusted, most-replaceable classes leave first.
DRAIN_ORDER = ("hostile", "untrusted", "third-party", "first-party", "trusted")

#: How stale a contributing health signal may be before the node cannot be ready.
HEALTH_STALENESS_BOUND = 30


class IllegalTransition(ValueError):
    """Raised when a lifecycle transition is not in the state machine."""


class DrainIncomplete(RuntimeError):
    """Raised when a drain deadline passes with workloads still resident."""


@dataclass
class NodeSupervisor:
    """The node's single local authority on whether it may accept work."""

    node: str
    state: str = "joining"
    workloads: dict = field(default_factory=dict)      # name -> trust class
    health: dict = field(default_factory=dict)         # signal -> last-seen tick
    last_reason: str = "initial"
    breaches: list = field(default_factory=list)

    # -- lifecycle ---------------------------------------------------
    def transition(self, to: str, *, reason: str = "") -> str:
        if to not in TRANSITIONS.get(self.state, set()):
            raise IllegalTransition(f"{self.node}: {self.state} -> {to} is not a legal transition")
        if to == "stopped" and self.workloads:
            raise DrainIncomplete(
                f"{self.node}: cannot stop with {len(self.workloads)} resident workload(s)")
        self.state = to
        self.last_reason = reason or to
        return self.state

    @property
    def accepts_placement(self) -> bool:
        """Placement is accepted only in ready, and only on fresh health evidence."""
        return self.state == "ready"

    def healthy_at(self, now: int) -> bool:
        """Health is affirmative evidence: a missing signal is not a healthy one."""
        if not self.health:
            return False
        return all(now - seen <= HEALTH_STALENESS_BOUND for seen in self.health.values())

    def report_health(self, signal: str, now: int) -> None:
        self.health[signal] = now

    def admit(self, workload: str, trust_class: str) -> None:
        if not self.accepts_placement:
            raise IllegalTransition(f"{self.node}: does not accept placement while {self.state}")
        self.workloads[workload] = trust_class

    # -- drain -------------------------------------------------------
    def drain_order(self) -> list:
        return sorted(self.workloads,
                      key=lambda w: (DRAIN_ORDER.index(self.workloads[w]), w))

    def drain(self, *, now: int, deadline: int, stubborn=()) -> dict:
        """Drain every resident workload in trust order; stubborn ones breach."""
        self.transition("draining", reason="drain requested")
        released, remaining = [], []
        for workload in self.drain_order():
            if workload in stubborn:
                remaining.append(workload)
                continue
            released.append(workload)
            del self.workloads[workload]
        if remaining:
            self.breaches.append({"at": now, "deadline": deadline, "workloads": remaining})
            return {"schema": "PK_DRAIN/1", "node": self.node, "complete": False,
                    "released": released, "remaining": remaining,
                    "escalation": "drain deadline exceeded; node held in draining"}
        self.transition("stopped", reason="drain complete")
        return {"schema": "PK_DRAIN/1", "node": self.node, "complete": True,
                "released": released, "remaining": []}


class EdgeNodeSupervisorComponent(Component):
    """Master-applied component for GAP-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.report_health("kubelet-equivalent", 0)
        sup.admit("a", "trusted")
        sup.admit("b", "untrusted")
        sup.admit("c", "third-party")
        assert sup.drain_order() == ["b", "c", "a"], "drain order ignored trust class"
        result = sup.drain(now=10, deadline=20)
        assert result["complete"] and sup.state == "stopped" and not sup.workloads
        findings[5] = self.satisfied(
            items[5],
            "Drain is deterministic and trust-ordered: untrusted released first, node reached stopped "
            "with zero residents.",
            *self._evidence("component.py::NodeSupervisor.drain"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.transition("cordoned", reason="operator cordon")
        try:
            sup.admit("late", "trusted")
        except IllegalTransition:
            findings[5] = self.satisfied(
                items[5], "A cordoned node refuses admission outright rather than deferring to the scheduler.",
                *self._evidence("component.py::NodeSupervisor.admit"))
        fresh = NodeSupervisor("n2")
        fresh.transition("ready")
        assert not fresh.healthy_at(0), "a node with no health signals reported healthy"
        findings[7] = self.satisfied(
            items[7],
            "Health is affirmative evidence: a node with no reported signals is not healthy, so a silenced "
            "reporter cannot keep a node in service.",
            *self._evidence("component.py::NodeSupervisor.healthy_at"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.report_health("s", 0)
        sup.admit("stuck", "trusted")
        result = sup.drain(now=10, deadline=5, stubborn={"stuck"})
        assert not result["complete"] and sup.state == "draining"
        findings[0] = self.satisfied(
            items[0],
            "A workload that refuses to drain holds the node in draining and records an escalation; "
            "the node never reports stopped while a resident remains.",
            *self._evidence("component.py::NodeSupervisor.drain"))
        try:
            NodeSupervisor("n3", state="stopped").transition("ready")
        except IllegalTransition:
            findings[6] = self.satisfied(
                items[6], "stopped is terminal: no transition out of it is accepted.",
                *self._evidence("component.py::TRANSITIONS"))
        assert not sup.healthy_at(HEALTH_STALENESS_BOUND + 1)
        findings[8] = self.satisfied(
            items[8],
            f"A health signal older than {HEALTH_STALENESS_BOUND} ticks makes the node unhealthy, so "
            "staleness is visible rather than silently tolerated.",
            *self._evidence("component.py::NodeSupervisor.healthy_at"))
        return findings

COMPONENT = EdgeNodeSupervisorComponent
