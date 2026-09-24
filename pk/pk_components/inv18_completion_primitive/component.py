"""INV-18 - Completion primitive.

The completion primitive is the one-shot counterpart to a stream: exactly one value, delivered once, to exactly one receiver. Having it as its own type rather than a stream of length one means the compiler knows there is no second value coming, so the receiver needs no loop and the writer cannot accidentally send twice.

The component answers all 100 requirements of the INV-18 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass


class AlreadyResolved(RuntimeError):
    """Raised on a second resolution of the same future."""


class AlreadyTaken(RuntimeError):
    """Raised when a second receiver tries to take the value."""


class Abandoned(RuntimeError):
    """Raised when the writer was dropped without resolving."""


_UNSET = object()


@dataclass
class Future:
    """A typed, one-shot completion.

    The point of a distinct primitive is what it rules out: there is no second
    value, so the receiver needs no loop, and the writer's second resolution is
    an error rather than an overwrite.
    """

    value_type: type
    _value: object = _UNSET
    _error: object = None
    taken: bool = False
    abandoned: bool = False

    @property
    def resolved(self) -> bool:
        return self._value is not _UNSET or self._error is not None

    def resolve(self, value) -> None:
        if self.resolved:
            raise AlreadyResolved("future already resolved")
        if not isinstance(value, self.value_type):
            raise TypeError(
                f"{type(value).__name__} for a future of {self.value_type.__name__}")
        self._value = value

    def resolve_error(self, error: str) -> None:
        """An error is an outcome, not an exception path: it resolves the future."""
        if self.resolved:
            raise AlreadyResolved("future already resolved")
        self._error = error

    def abandon(self) -> None:
        self.abandoned = True

    def take(self):
        """Return ``("ok", value)`` or ``("error", message)``."""
        if self.taken:
            raise AlreadyTaken("future already taken by its receiver")
        if not self.resolved:
            if self.abandoned:
                raise Abandoned("writer dropped without resolving")
            return None
        self.taken = True
        if self._error is not None:
            return ("error", self._error)
        return ("ok", self._value)


class CompletionPrimitiveComponent(Component):
    """Master-applied component for INV-18."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        f = Future(str)
        f.resolve("done")
        twice = False
        try:
            f.resolve("again")
        except AlreadyResolved:
            twice = True
        assert twice and f.take() == ("ok", "done")
        second = False
        try:
            f.take()
        except AlreadyTaken:
            second = True
        assert second
        findings[0] = self.satisfied(
            items[0],
            "A future resolves at most once and is taken by at most one receiver; the second resolution "
            "and the second take both raise rather than overwriting or duplicating the value.",
            *self._evidence("component.py::Future.resolve", "component.py::Future.take"))

        e = Future(str)
        e.resolve_error("upstream refused")
        assert e.take() == ("error", "upstream refused")
        findings[1] = self.satisfied(
            items[1],
            "An error resolution is an ordinary outcome carried in the same handle, so a receiver reads a "
            "tagged result rather than distinguishing failure by a side channel.",
            *self._evidence("component.py::Future.resolve_error"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        f = Future(str)
        f.abandon()
        orphaned = False
        try:
            f.take()
        except Abandoned:
            orphaned = True
        assert orphaned
        findings[0] = self.satisfied(
            items[0],
            "A writer dropped without resolving raises on the receiver instead of leaving it waiting "
            "forever, so an abandoned completion is a failure the caller can handle.",
            *self._evidence("component.py::Future.take"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        f = Future(int)
        wrong = False
        try:
            f.resolve("not an int")
        except TypeError:
            wrong = True
        assert wrong and not f.resolved
        findings[1] = self.satisfied(
            items[1],
            "The value type is part of the handle, so a mistyped resolution is refused and leaves the "
            "future unresolved rather than delivering a value the receiver cannot lift.",
            *self._evidence("component.py::Future.resolve"))
        return findings

COMPONENT = CompletionPrimitiveComponent
