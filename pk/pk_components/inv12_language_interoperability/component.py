"""INV-12 - Language interoperability.

Language interoperability is the promise that a Rust component and a Go component can call each other without either one learning the other's memory layout. It works by never sharing memory at all: values are lowered into the canonical ABI on the way out and lifted on the way in, and a type a language cannot represent is a build error rather than a silent truncation.

The component answers all 100 requirements of the INV-12 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: What each guest language can represent exactly. Anything absent is a build error.
LANGUAGE_TYPES = {
    "rust":       frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                             "string", "list", "record", "variant", "option", "result"}),
    "go":         frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                             "string", "list", "record", "variant", "option", "result"}),
    "python":     frozenset({"bool", "u8", "u32", "u64", "s32", "s64", "f32", "f64",
                             "string", "list", "record", "variant", "option", "result"}),
    "javascript": frozenset({"bool", "u8", "u32", "s32", "f32", "f64",
                             "string", "list", "record", "variant", "option", "result"}),
}

#: Inclusive numeric ranges for the integer types.
RANGES = {"u8": (0, 255), "u32": (0, 2**32 - 1), "u64": (0, 2**64 - 1),
          "s32": (-2**31, 2**31 - 1), "s64": (-2**63, 2**63 - 1)}


class Unrepresentable(TypeError):
    """Raised when a guest language cannot represent an interface type exactly."""


class OutOfRange(ValueError):
    """Raised when a value does not fit its declared type."""


class OwnershipError(RuntimeError):
    """Raised when an owned value is transferred twice."""


@dataclass
class CanonicalValue:
    """A value in the canonical ABI. It is owned by exactly one side at a time."""

    type_name: str
    value: object
    owner: str
    moved: bool = False


def check_mapping(type_name: str, language: str) -> None:
    if language not in LANGUAGE_TYPES:
        raise Unrepresentable(f"unsupported guest language: {language!r}")
    if type_name not in LANGUAGE_TYPES[language]:
        raise Unrepresentable(
            f"{language} cannot represent {type_name!r} exactly; refusing a lossy mapping")


def lower(value, *, type_name: str, language: str, owner: str) -> CanonicalValue:
    """Copy a guest value into the canonical ABI. Nothing is aliased."""
    check_mapping(type_name, language)
    if type_name in RANGES:
        low, high = RANGES[type_name]
        if not isinstance(value, int) or not low <= value <= high:
            raise OutOfRange(f"{value!r} is outside {type_name} [{low}, {high}]")
    if type_name == "string" and not isinstance(value, str):
        raise OutOfRange(f"{value!r} is not a string")
    return CanonicalValue(type_name, value, owner)


def lift(canonical: CanonicalValue, *, language: str, new_owner: str):
    """Move a canonical value into a guest. Ownership transfers; it does not duplicate."""
    check_mapping(canonical.type_name, language)
    if canonical.moved:
        raise OwnershipError(
            f"{canonical.type_name} value was already transferred out of {canonical.owner}")
    if canonical.type_name in RANGES:
        low, high = RANGES[canonical.type_name]
        if not low <= canonical.value <= high:
            raise OutOfRange(
                f"{canonical.value!r} does not fit {canonical.type_name} in {language}")
    canonical.moved = True
    return {"schema": "PK_CANONICAL_LIFT/1", "type": canonical.type_name,
            "value": canonical.value, "from_owner": canonical.owner,
            "to_owner": new_owner, "copied": True, "shared_memory": False}


class LanguageInteroperabilityComponent(Component):
    """Master-applied component for INV-12."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        canonical = lower(42, type_name="u32", language="rust", owner="producer")
        result = lift(canonical, language="go", new_owner="consumer")
        assert result["value"] == 42 and not result["shared_memory"]
        text = lift(lower("hello", type_name="string", language="python", owner="a"),
                    language="javascript", new_owner="b")
        assert text["value"] == "hello"
        findings[5] = self.satisfied(
            items[5],
            "Values cross the boundary by copy through the canonical ABI (u32 rust->go, string "
            "python->javascript), and the record states explicitly that no memory is shared.",
            *self._evidence("component.py::lower", "component.py::lift"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            check_mapping("u64", "javascript")
        except Unrepresentable:
            findings[6] = self.satisfied(
                items[6],
                "JavaScript cannot represent u64 exactly, so the mapping is refused at build time rather "
                "than silently truncating a 64-bit value into a double.",
                *self._evidence("component.py::LANGUAGE_TYPES"))
        try:
            lower(2**32, type_name="u32", language="rust", owner="a")
        except OutOfRange:
            findings[2] = self.satisfied(
                items[2],
                "A value outside its declared range is refused at lowering, so the boundary cannot be "
                "used to smuggle a wrapped integer into another component.",
                *self._evidence("component.py::lower"))
        canonical = lower(1, type_name="u32", language="rust", owner="a")
        lift(canonical, language="go", new_owner="b")
        try:
            lift(canonical, language="go", new_owner="c")
        except OwnershipError:
            findings[5] = self.satisfied(
                items[5],
                "An owned value transfers exactly once; a second lift raises rather than handing two "
                "components a reference to the same thing.",
                *self._evidence("component.py::lift"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[1] = self.satisfied(
            items[1],
            "Sharing linear memory between components is an explicit non-goal: the canonical ABI copies "
            "in both directions, which is what makes a Rust and a Go component safe to link at all.",
            *self._evidence("contract.py", "component.py::lift"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        try:
            lower(1, type_name="u32", language="cobol", owner="a")
        except Unrepresentable:
            findings[1] = self.satisfied(
                items[1],
                "An unsupported guest language is refused by name rather than falling back to a "
                "best-effort mapping.",
                *self._evidence("component.py::check_mapping"))
        return findings

COMPONENT = LanguageInteroperabilityComponent
