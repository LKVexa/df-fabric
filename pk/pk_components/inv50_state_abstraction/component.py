"""INV-50 - State abstraction.

The state abstraction is a key/value contract with the concurrency rules written down: every value carries an etag, a write that names a stale etag is refused, and keys are namespaced by application so two apps sharing a store cannot read each other's data by picking the same key.

The component answers all 100 requirements of the INV-50 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import itertools
from dataclasses import dataclass, field

_etags = itertools.count(1)


class EtagMismatch(RuntimeError):
    """Raised when a write names an etag the store no longer holds."""


@dataclass
class StateStore:
    data: dict = field(default_factory=dict)       # full key -> (value, etag)
    conflicts: int = 0

    @staticmethod
    def key(app: str, k: str) -> str:
        return f"{app}||{k}"

    def get(self, app: str, k: str):
        return self.data.get(self.key(app, k), (None, None))

    def set(self, app: str, k: str, value, etag=None, mode: str = "first-write"):
        full = self.key(app, k)
        current = self.data.get(full, (None, None))[1]
        if mode == "first-write" and etag is not None and etag != current:
            self.conflicts += 1
            raise EtagMismatch(f"{k}: have {current}, given {etag}")
        new = next(_etags)
        self.data[full] = (value, new)
        return new

    def bulk_set(self, app: str, writes):
        """All-or-nothing: every etag is checked before any value is written."""
        for k, _v, etag in writes:
            current = self.data.get(self.key(app, k), (None, None))[1]
            if etag is not None and etag != current:
                self.conflicts += 1
                raise EtagMismatch(f"bulk aborted at {k}")
        return [self.set(app, k, v) for k, v, _ in writes]


class StateAbstractionComponent(Component):
    """Master-applied component for INV-50."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        s = StateStore()
        s.set("cart", "c1", 1)
        _, etag = s.get("cart", "c1")
        s.set("cart", "c1", 2, etag=etag)          # writer A wins
        lost = False
        try:
            s.set("cart", "c1", 99, etag=etag)     # writer B, same stale etag
        except EtagMismatch:
            lost = True
        assert lost and s.get("cart", "c1")[0] == 2
        findings[0] = self.satisfied(
            items[0],
            "Two writers holding the same etag race; the second is refused with an etag mismatch and "
            "the first writer's value stands, so concurrent updates cannot silently overwrite each other.",
            *self._evidence("component.py::StateStore.set"))

        s.set("cart", "a", 1)
        _, ea = s.get("cart", "a")
        aborted = False
        try:
            s.bulk_set("cart", [("a", 10, ea), ("b", 20, 12345)])
        except EtagMismatch:
            aborted = True
        assert aborted and s.get("cart", "a")[0] == 1 and s.get("cart", "b")[0] is None
        findings[1] = self.satisfied(
            items[1],
            "A bulk write with one stale etag aborts before touching anything: neither key changed.",
            *self._evidence("component.py::StateStore.bulk_set"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        s = StateStore()
        s.set("billing", "secret", "card-token")
        assert s.get("shop", "secret") == (None, None)
        findings[0] = self.satisfied(
            items[0],
            "Keys are namespaced by application, so another application asking for the same key name "
            "gets nothing rather than the billing application's value.",
            *self._evidence("component.py::StateStore.key"))
        return findings

COMPONENT = StateAbstractionComponent
