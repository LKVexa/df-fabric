"""INV-57 - Durable execution.

Durable execution makes a long-running workflow survive crashes by recording what happened rather than where the code was. Each activity's result goes into a history; after a crash the workflow code re-runs from the top and every completed activity returns its recorded result instead of running again. That only works if the workflow code is deterministic, so divergence from the history is detected and refused.

The component answers all 100 requirements of the INV-57 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class NonDeterminism(RuntimeError):
    pass


class Crash(RuntimeError):
    """Simulated worker crash."""


@dataclass
class Worker:
    history: list = field(default_factory=list)     # [(activity_name, result)]
    executed: list = field(default_factory=list)
    _pos: int = 0

    def activity(self, name: str, fn):
        if self._pos < len(self.history):
            recorded_name, result = self.history[self._pos]
            if recorded_name != name:
                raise NonDeterminism(
                    f"step {self._pos}: history has {recorded_name!r}, code asked for {name!r}")
            self._pos += 1
            return result
        result = fn()
        self.executed.append(name)
        self.history.append((name, result))
        self._pos += 1
        return result

    def run(self, workflow):
        self._pos = 0
        return workflow(self)


class DurableExecutionComponent(Component):
    """Master-applied component for INV-57."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        charges = []
        crash_once = {"armed": True}

        def order(w):
            w.activity("reserve", lambda: "r-1")
            w.activity("charge", lambda: charges.append(1) or "c-1")
            if crash_once["armed"]:
                crash_once["armed"] = False
                raise Crash()
            return w.activity("ship", lambda: "s-1")

        w = Worker()
        try:
            w.run(order)
        except Crash:
            pass
        result = w.run(order)                    # resumed from history
        assert result == "s-1" and len(charges) == 1 and w.executed == ["reserve", "charge", "ship"]
        findings[0] = self.satisfied(
            items[0],
            "A workflow that crashed after charging resumes by replaying its history: reserve and "
            "charge return their recorded results, the card is charged once, and only 'ship' runs new.",
            *self._evidence("component.py::Worker.activity"))
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        w = Worker()
        w.run(lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        caught = False
        try:
            w.run(lambda w: [w.activity("a", lambda: 1), w.activity("c", lambda: 3)])
        except NonDeterminism:
            caught = True
        assert caught and w.executed == ["a", "b"]
        findings[0] = self.satisfied(
            items[0],
            "Workflow code that takes a different path on replay is detected at the diverging step and "
            "refused before it runs any new activity.",
            *self._evidence("component.py::Worker.activity"))
        return findings

COMPONENT = DurableExecutionComponent
