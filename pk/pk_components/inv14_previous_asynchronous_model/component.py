"""INV-14 - Previous asynchronous model.

The previous asynchronous model is the poll-based one: a component hands the host a list of pollables and blocks until one is ready. It works, it is simple, and it does not compose -- which is exactly why the new ABI exists. This element keeps it running honestly while it is still deployed, and states what it cannot do.

The component answers all 100 requirements of the INV-14 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

MIGRATION_TARGET = "INV-15 New asynchronous ABI"


class ForeignPollable(PermissionError):
    """Raised when a pollable from another instance is polled."""


@dataclass
class Pollable:
    """A readiness handle. It belongs to exactly one instance and does not travel."""

    name: str
    owner: str
    ready: bool = False
    #: Readiness that arrived while a poll was in flight, so it cannot be lost.
    pending_signal: bool = False

    def signal(self) -> None:
        if self.ready:
            return
        self.pending_signal = True


@dataclass
class PollSet:
    """The legacy blocking primitive: bounded, lossless, and deprecated."""

    owner: str
    deprecated_uses: int = 0

    def poll(self, pollables: list, *, timeout_ticks: int) -> dict:
        self.deprecated_uses += 1
        if timeout_ticks <= 0:
            raise ValueError("poll requires a positive timeout; unbounded blocking is refused")
        if not pollables:
            raise ValueError("poll on an empty set would block forever")
        foreign = [p.name for p in pollables if p.owner != self.owner]
        if foreign:
            raise ForeignPollable(
                f"{self.owner}: pollables {foreign} belong to another instance and do not compose")

        # Any signal delivered during the window is folded in before the verdict,
        # so a wakeup that raced the poll is never dropped.
        for p in pollables:
            if p.pending_signal:
                p.ready, p.pending_signal = True, False

        ready = [p.name for p in pollables if p.ready]
        return {"schema": "PK_POLL/1", "owner": self.owner,
                "ready": ready, "timed_out": not ready,
                "timeout_ticks": timeout_ticks,
                "set_size": len(pollables),
                "deprecated": True,
                "migrate_to": MIGRATION_TARGET}


class PreviousAsynchronousModelComponent(Component):
    """Master-applied component for INV-14."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        a, b = Pollable("net", "inst-1"), Pollable("timer", "inst-1")
        ps = PollSet("inst-1")
        idle = ps.poll([a, b], timeout_ticks=10)
        assert idle["timed_out"] and idle["deprecated"]
        b.signal()
        woken = ps.poll([a, b], timeout_ticks=10)
        assert woken["ready"] == ["timer"] and not woken["timed_out"]
        findings[5] = self.satisfied(
            items[5],
            "Polling is bounded and deterministic: an idle set times out, and a signalled pollable is "
            f"reported ready. Every result carries the deprecation and names {MIGRATION_TARGET}.",
            *self._evidence("component.py::PollSet.poll"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Pollable("net", "inst-1")
        ps = PollSet("inst-1")
        p.signal()                      # readiness races the poll
        result = ps.poll([p], timeout_ticks=5)
        assert result["ready"] == ["net"], "a wakeup that raced the poll was lost"
        findings[0] = self.satisfied(
            items[0],
            "A readiness signal that arrives while a poll is in flight is folded in before the verdict, "
            "so the classic lost-wakeup stall cannot happen.",
            *self._evidence("component.py::PollSet.poll"))
        proven = []
        for label, args in [("unbounded blocking", ([Pollable("x", "inst-1")], 0)),
                            ("empty set", ([], 10))]:
            try:
                ps.poll(args[0], timeout_ticks=args[1])
            except ValueError:
                proven.append(label)
        assert len(proven) == 2
        findings[5] = self.satisfied(
            items[5],
            f"Both ways of blocking forever are refused ({', '.join(proven)}), so the legacy model cannot "
            "be used to pin a component.",
            *self._evidence("component.py::PollSet.poll"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        ps = PollSet("inst-1")
        try:
            ps.poll([Pollable("other", "inst-2")], timeout_ticks=5)
        except ForeignPollable:
            findings[7] = self.satisfied(
                items[7],
                "Pollables do not cross component boundaries -- that non-composability is the model's "
                "defining limit and the reason INV-15 exists, so it is enforced rather than papered over.",
                *self._evidence("component.py::PollSet.poll", "contract.py"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        ps = PollSet("inst-1")
        ps.poll([Pollable("a", "inst-1")], timeout_ticks=1)
        ps.poll([Pollable("b", "inst-1")], timeout_ticks=1)
        assert ps.deprecated_uses == 2
        findings[8] = self.satisfied(
            items[8],
            f"Deprecated use is counted per instance ({ps.deprecated_uses} so far), so migration progress "
            "off this model is a measurable number rather than an intention.",
            *self._evidence("component.py::PollSet"))
        return findings

COMPONENT = PreviousAsynchronousModelComponent
