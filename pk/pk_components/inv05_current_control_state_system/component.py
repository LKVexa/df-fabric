"""INV-05 - Current control-state system.

The current control-state system is the consistent key-value store every controller reads and writes: each change gets a revision number, updates are compare-and-swap, and controllers watch for changes from a revision onward. The trap is compaction -- a watcher that asks for history that has been discarded must be told so, not silently given a gap.

The component answers all 100 requirements of the INV-05 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class Compacted(LookupError):
    pass


@dataclass
class ControlState:
    revision: int = 0
    data: dict = field(default_factory=dict)       # key -> (value, mod_revision)
    history: list = field(default_factory=list)    # (revision, key, value)
    compacted_at: int = 0

    def txn(self, compare: dict, ops: dict) -> bool:
        """compare: key -> expected mod_revision (0 = must not exist)."""
        for k, rev in compare.items():
            if self.data.get(k, (None, 0))[1] != rev:
                return False
        for k, v in ops.items():
            self.revision += 1
            self.data[k] = (v, self.revision)
            self.history.append((self.revision, k, v))
        return True

    def watch(self, from_rev: int) -> list:
        if from_rev <= self.compacted_at:
            raise Compacted(f"revision {from_rev} compacted (history starts after {self.compacted_at}); relist")
        return [h for h in self.history if h[0] >= from_rev]

    def compact(self, rev: int) -> int:
        before = len(self.history)
        self.history = [h for h in self.history if h[0] > rev]
        self.compacted_at = max(self.compacted_at, rev)
        return before - len(self.history)


class CurrentControlStateSystemComponent(Component):
    """Master-applied component for INV-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        s = ControlState()
        assert s.txn({"lease/a": 0}, {"lease/a": "node-1"})
        rev = s.data["lease/a"][1]
        assert s.txn({"lease/a": rev}, {"lease/a": "node-2"})
        assert not s.txn({"lease/a": rev}, {"lease/a": "node-3"})
        assert s.data["lease/a"][0] == "node-2"
        findings[0] = self.satisfied(
            items[0],
            "Writes are compare-and-swap on the key's revision: two controllers acting on the same "
            "revision cannot both win, so the second is refused and the first holder keeps the lease.",
            *self._evidence("component.py::ControlState.txn"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = ControlState()
        for i in range(10):
            s.txn({}, {f"k{i}": i})
        assert len(s.watch(5)) == 6
        dropped = s.compact(6)
        gap = False
        try:
            s.watch(5)
        except Compacted:
            gap = True
        assert gap and dropped == 6 and [h[0] for h in s.watch(7)] == [7, 8, 9, 10]
        findings[0] = self.satisfied(
            items[0],
            f"After compaction discards {dropped} old revisions, a controller asking to resume from a "
            "discarded revision is told explicitly to relist instead of being handed a stream with a "
            "silent gap; watches after the compaction point still receive every change.",
            *self._evidence("component.py::ControlState.watch", "component.py::ControlState.compact"))
        return findings

COMPONENT = CurrentControlStateSystemComponent
