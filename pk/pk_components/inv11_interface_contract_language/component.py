"""INV-11 - Interface contract language.

The interface contract language is WIT: the typed vocabulary that says what crosses a component boundary. It is the only thing standing between two components written in different languages and a memory-safety incident, so compatibility here is structural and checked, never assumed from a version number.

The component answers all 100 requirements of the INV-11 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

ADDITIVE, COMPATIBLE, BREAKING = "additive", "compatible", "breaking"


class Incompatible(TypeError):
    """Raised when two interfaces cannot be linked."""


@dataclass(frozen=True)
class Func:
    """One function in an interface: its parameter and result types."""

    name: str
    params: tuple           # ((name, type), ...)
    results: tuple          # (type, ...) -- a variant's cases when it is a variant


@dataclass(frozen=True)
class Interface:
    """A typed interface. Identity is structural; the version is just a label."""

    name: str
    version: str
    functions: frozenset    # of Func

    def by_name(self) -> dict:
        return {f.name: f for f in self.functions}


def classify(old: Interface, new: Interface) -> dict:
    """Classify a change by comparing structure, not version numbers."""
    if old.name != new.name:
        raise ValueError("cannot compare two differently named interfaces")
    o, n = old.by_name(), new.by_name()
    reasons, cls = [], ADDITIVE

    removed = sorted(set(o) - set(n))
    if removed:
        reasons.append(f"functions removed: {removed}")
        cls = BREAKING

    for name in sorted(set(o) & set(n)):
        if o[name].params != n[name].params:
            reasons.append(f"{name}: parameter types changed")
            cls = BREAKING
        elif set(n[name].results) > set(o[name].results):
            # A new result case is something existing consumers cannot handle.
            reasons.append(f"{name}: new result case(s) "
                           f"{sorted(set(n[name].results) - set(o[name].results))}")
            cls = BREAKING
        elif o[name].results != n[name].results:
            reasons.append(f"{name}: result types changed")
            cls = BREAKING

    added = sorted(set(n) - set(o))
    if added and cls == ADDITIVE:
        reasons.append(f"functions added: {added}")
    elif not added and not reasons:
        cls = COMPATIBLE
        reasons.append("structurally identical")

    return {"schema": "PK_INTERFACE_DIFF/1", "interface": old.name,
            "from": old.version, "to": new.version,
            "class": cls, "reasons": reasons,
            "linkable": cls != BREAKING}


def check_link(producer: Interface, consumer: Interface) -> dict:
    """A consumer links to a producer only if the producer offers everything it needs, identically."""
    p, c = producer.by_name(), consumer.by_name()
    missing = sorted(set(c) - set(p))
    if missing:
        raise Incompatible(
            f"{producer.name}: producer does not offer {missing}")
    for name in sorted(c):
        if p[name].params != c[name].params or p[name].results != c[name].results:
            raise Incompatible(
                f"{name}: producer and consumer signatures differ structurally")
    return {"schema": "PK_INTERFACE/1", "interface": producer.name,
            "producer_version": producer.version, "consumer_version": consumer.version,
            "linked": True, "functions": sorted(c)}


class InterfaceContractLanguageComponent(Component):
    """Master-applied component for INV-11."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        get = Func("get", (("key", "string"),), ("ok", "not-found"))
        v1 = Interface("wasi:kv/store", "1.0.0", frozenset({get}))
        v2 = Interface("wasi:kv/store", "1.1.0",
                       frozenset({get, Func("delete", (("key", "string"),), ("ok",))}))
        change = classify(v1, v2)
        assert change["class"] == ADDITIVE and change["linkable"]
        assert check_link(v2, v1)["linked"], "an older consumer could not link to a newer producer"
        findings[5] = self.satisfied(
            items[5],
            f"Adding a function is classified {change['class']} and an older consumer still links to the "
            "newer producer, because compatibility is computed from structure.",
            *self._evidence("component.py::classify", "component.py::check_link"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (("a", "string"),), ("ok",))}))
        narrowed = Interface("i", "1.0.1", frozenset({Func("f", (("a", "u32"),), ("ok",))}))
        change = classify(v1, narrowed)
        assert change["class"] == BREAKING and not change["linkable"]
        findings[6] = self.satisfied(
            items[6],
            f"A parameter type change shipped as a patch version ({change['from']} -> {change['to']}) is "
            "still classified breaking, so the version string cannot launder a type confusion.",
            *self._evidence("component.py::classify"))
        try:
            check_link(narrowed, v1)
        except Incompatible:
            findings[5] = self.satisfied(
                items[5],
                "Structurally mismatched signatures refuse to link, which is the boundary keeping two "
                "differently-compiled languages from disagreeing about memory.",
                *self._evidence("component.py::check_link"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (), ("ok", "err"))}))
        v2 = Interface("i", "2.0.0", frozenset({Func("f", (), ("ok", "err", "throttled"))}))
        change = classify(v1, v2)
        assert change["class"] == BREAKING
        findings[3] = self.satisfied(
            items[3],
            "Adding a result case is breaking, not additive: an existing consumer has no arm for "
            "'throttled', so the change is refused rather than shipped as backward compatible.",
            *self._evidence("component.py::classify"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (), ("ok",)),
                                                Func("g", (), ("ok",))}))
        v2 = Interface("i", "1.1.0", frozenset({Func("f", (), ("ok",))}))
        change = classify(v1, v2)
        assert change["class"] == BREAKING and "removed" in change["reasons"][0]
        findings[0] = self.satisfied(
            items[0],
            "Removing a function is detected as breaking with the removed names reported, so the failure "
            "is explained rather than discovered by a consumer at run time.",
            *self._evidence("component.py::classify"))
        return findings

COMPONENT = InterfaceContractLanguageComponent
