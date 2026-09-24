"""INV-10 - Component composition system.

The component composition system is what makes modules into something you can actually wire together: each component states its imports and exports as typed interfaces, and composition is linking them. A composition either closes -- every import satisfied by some export -- or it is not a composition at all.

The component answers all 100 requirements of the INV-10 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field


class UnsatisfiedImport(ValueError):
    """Raised when a composition leaves an internal import with no export."""


class AmbiguousExport(ValueError):
    """Raised when two components export the same interface within one composition."""


class CompositionCycle(ValueError):
    """Raised when components depend on each other in a cycle."""


@dataclass(frozen=True)
class Unit:
    """A unit of composition: what it needs, and what it offers."""

    name: str
    imports: frozenset
    exports: frozenset


def compose(components: list, *, external: frozenset = frozenset()) -> dict:
    """Link components into a closed composition, or refuse."""
    provider = {}
    for component in sorted(components, key=lambda c: c.name):
        for interface in sorted(component.exports):
            if interface in provider:
                raise AmbiguousExport(
                    f"{interface!r} exported by both {provider[interface]} and {component.name}")
            provider[interface] = component.name

    edges, remaining = {}, set()
    for component in components:
        deps = set()
        for interface in component.imports:
            if interface in provider:
                deps.add(provider[interface])
            elif interface in external:
                remaining.add(interface)
            else:
                raise UnsatisfiedImport(
                    f"{component.name}: import {interface!r} has no export and is not external")
        edges[component.name] = deps - {component.name}

    # Topological ordering: a cycle means instantiation could never terminate.
    pending = {k: set(v) for k, v in edges.items()}
    order = []
    while pending:
        ready = sorted(k for k, deps in pending.items() if not deps)
        if not ready:
            raise CompositionCycle(f"dependency cycle among {sorted(pending)}")
        for name in ready:
            order.append(name)
            del pending[name]
        for deps in pending.values():
            deps.difference_update(ready)

    body = {"components": sorted(c.name for c in components),
            "order": order,
            "external_imports": sorted(remaining),
            "exports": sorted(provider)}
    body["composition"] = hashlib.sha256(
        repr(sorted(body.items())).encode()).hexdigest()[:24]
    body["schema"] = "PK_COMPOSITION/1"
    body["closed"] = True
    return body


class ComponentCompositionSystemComponent(Component):
    """Master-applied component for INV-10."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        parts = [
            Unit("store", frozenset(), frozenset({"wasi:kv/store"})),
            Unit("api", frozenset({"wasi:kv/store"}), frozenset({"wasi:http/handler"})),
        ]
        result = compose(parts)
        assert result["closed"] and result["order"] == ["store", "api"]
        assert result["external_imports"] == []
        again = compose(list(reversed(parts)))
        assert again["composition"] == result["composition"], "composition id is order-dependent"
        findings[5] = self.satisfied(
            items[5],
            f"Linking is deterministic and produces an instantiation order ({' -> '.join(result['order'])}) "
            f"with a content-addressed id ({result['composition'][:12]}) independent of input order.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        parts = [Unit("api", frozenset({"wasi:http/outgoing"}), frozenset())]
        result = compose(parts, external=frozenset({"wasi:http/outgoing"}))
        assert result["external_imports"] == ["wasi:http/outgoing"]
        findings[8] = self.satisfied(
            items[8],
            "An import the composition does not satisfy internally surfaces as an explicit external "
            "import rather than being quietly deferred to run time.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            compose([Unit("api", frozenset({"wasi:kv/store"}), frozenset())])
        except UnsatisfiedImport:
            findings[6] = self.satisfied(
                items[6],
                "An import with no export and no external declaration refuses the composition, so nothing "
                "reaches run time hoping an implementation will turn up.",
                *self._evidence("component.py::compose"))
        try:
            compose([Unit("a", frozenset(), frozenset({"i"})),
                     Unit("b", frozenset(), frozenset({"i"}))])
        except AmbiguousExport:
            findings[0] = self.satisfied(
                items[0],
                "Two components exporting the same interface is ambiguous and refused, so an import "
                "cannot be silently bound to an unintended provider.",
                *self._evidence("component.py::compose"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        try:
            compose([Unit("a", frozenset({"i-b"}), frozenset({"i-a"})),
                     Unit("b", frozenset({"i-a"}), frozenset({"i-b"}))])
        except CompositionCycle:
            findings[6] = self.satisfied(
                items[6],
                "A dependency cycle is detected at composition time rather than becoming a "
                "non-terminating instantiation at run time.",
                *self._evidence("component.py::compose"))
        return findings

COMPONENT = ComponentCompositionSystemComponent
