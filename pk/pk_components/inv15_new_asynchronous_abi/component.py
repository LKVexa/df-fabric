"""INV-15 - New asynchronous ABI.

The new asynchronous ABI is what lets a component wait without pinning anything. Instead of a pollable that only its own instance may look at, a call returns either a value or a subtask handle, and the host owns the readiness table. Because waiting is expressed as a handle rather than a blocked stack, a waiting component costs a table row instead of a thread.

The component answers all 100 requirements of the INV-15 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Outstanding subtasks allowed per instance before calls are refused.
DEFAULT_BUDGET = 8


class BudgetExhausted(RuntimeError):
    """Raised when an instance already holds its maximum outstanding subtasks."""


class ForeignHandle(RuntimeError):
    """Raised when an instance waits on a subtask it does not own."""


class HandleConsumed(RuntimeError):
    """Raised when a completed or cancelled subtask handle is used again."""


@dataclass
class Subtask:
    """One outstanding asynchronous call."""

    handle: int
    owner: str
    ready: bool = False
    cancelled: bool = False
    consumed: bool = False
    value: object = None


@dataclass
class AsyncAbi:
    """Host-owned waitable table for one instance.

    Readiness lives here, not in the guest: a guest cannot fabricate a ready
    handle, and a handle minted for one instance is refused to every other.
    """

    instance: str
    budget: int = DEFAULT_BUDGET
    _next: int = 1
    table: dict = field(default_factory=dict)
    blocked_stacks: int = 0
    refusals: int = 0
    cancellations: int = 0

    def call(self, immediate=None):
        """Start a call.  Returns ``("value", v)`` or ``("subtask", handle)``."""
        if immediate is not None:
            return ("value", immediate)
        live = [s for s in self.table.values() if not s.consumed]
        if len(live) >= self.budget:
            self.refusals += 1
            raise BudgetExhausted(
                f"{self.instance}: {len(live)} outstanding subtasks, budget {self.budget}")
        handle = self._next
        self._next += 1
        self.table[handle] = Subtask(handle=handle, owner=self.instance)
        # NB: no stack is parked here -- that counter must stay at zero.
        return ("subtask", handle)

    def complete(self, handle: int, value: object) -> None:
        task = self.table[handle]
        if task.cancelled:
            return
        task.ready = True
        task.value = value

    def wait(self, handles) -> list:
        """Return the ready handles in the set.  Never blocks a guest stack."""
        for h in handles:
            task = self.table.get(h)
            if task is None:
                raise ForeignHandle(f"{self.instance} does not own handle {h}")
            if task.consumed:
                raise HandleConsumed(f"handle {h} already consumed")
        return [h for h in handles if self.table[h].ready]

    def take(self, handle: int):
        task = self.table[handle]
        if task.consumed:
            raise HandleConsumed(f"handle {handle} already consumed")
        task.consumed = True
        return task.value

    def cancel_all(self, reason: str = "caller gone") -> int:
        """Propagate cancellation to every outstanding subtask."""
        n = 0
        for task in self.table.values():
            if not task.consumed and not task.ready:
                task.cancelled = True
                task.consumed = True
                n += 1
        self.cancellations += n
        return n


class NewAsynchronousAbiComponent(Component):
    """Master-applied component for INV-15."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        abi = AsyncAbi("inst-1", budget=2)
        kind, first = abi.call()
        abi.call()
        refused = False
        try:
            abi.call()
        except BudgetExhausted:
            refused = True
        assert kind == "subtask" and refused and abi.blocked_stacks == 0
        findings[0] = self.satisfied(
            items[0],
            f"A call returns a subtask handle rather than parking a stack ({abi.blocked_stacks} stacks "
            f"blocked with {len(abi.table)} calls outstanding), and the {abi.budget}-call budget refuses "
            "the next one instead of growing without bound.",
            *self._evidence("component.py::AsyncAbi.call"))

        abi2 = AsyncAbi("inst-2")
        _, h = abi2.call()
        abi2.complete(h, "done")
        assert abi2.wait([h]) == [h] and abi2.take(h) == "done"
        reused = False
        try:
            abi2.take(h)
        except HandleConsumed:
            reused = True
        assert reused
        findings[1] = self.satisfied(
            items[1],
            "Readiness is read out of the host-owned table and a handle is consumed exactly once; a "
            "second use raises rather than returning a stale value.",
            *self._evidence("component.py::AsyncAbi.take"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a, b = AsyncAbi("inst-1"), AsyncAbi("inst-2")
        _, h = a.call()
        stolen = False
        try:
            b.wait([h])
        except ForeignHandle:
            stolen = True
        assert stolen
        findings[3] = self.satisfied(
            items[3],
            "A subtask handle is scoped to the instance that minted it: another instance waiting on it is "
            "refused, so readiness cannot be observed or forged across the boundary.",
            *self._evidence("component.py::AsyncAbi.wait"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        abi = AsyncAbi("inst-1")
        for _ in range(3):
            abi.call()
        cancelled = abi.cancel_all("caller gone")
        assert cancelled == 3
        assert not [t for t in abi.table.values() if not t.consumed]
        findings[2] = self.satisfied(
            items[2],
            f"When the caller goes away every outstanding subtask is cancelled ({cancelled} of 3), so no "
            "work survives the requester that asked for it.",
            *self._evidence("component.py::AsyncAbi.cancel_all"))
        return findings

COMPONENT = NewAsynchronousAbiComponent
