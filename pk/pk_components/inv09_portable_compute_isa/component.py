"""INV-09 - Portable compute ISA.

The portable compute ISA is the bytecode everything above it compiles to: a small, deterministic instruction set with no ambient environment and no undefined behaviour to exploit. Portability is only worth anything if the same module computes the same answer everywhere, so this element validates modules rather than trusting their headers.

The component answers all 100 requirements of the INV-09 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Features that make results diverge between hosts.
NON_DETERMINISTIC = frozenset({"float-relaxed", "simd-relaxed", "threads", "wall-clock"})

#: Profiles: what each permits.
PROFILES = {
    "deterministic": frozenset({"core", "bulk-memory", "reference-types", "multi-value"}),
    "extended": frozenset({"core", "bulk-memory", "reference-types", "multi-value", "simd"}),
    "permissive": frozenset({"core", "bulk-memory", "reference-types", "multi-value",
                             "simd", "simd-relaxed", "threads", "float-relaxed", "wall-clock"}),
}

MAX_SECTIONS = 64
MAX_BYTES = 4 * 1024 * 1024


class ValidationFailed(ValueError):
    """Raised when a module does not validate."""


class FeatureRefused(PermissionError):
    """Raised when a module uses a feature the profile does not permit."""


@dataclass(frozen=True)
class Module:
    """A compute module: what it says it needs, and what it actually uses."""

    name: str
    declared_features: frozenset
    used_features: frozenset
    sections: int = 8
    size_bytes: int = 1024
    well_formed: bool = True


def validate(module: Module, *, profile: str) -> dict:
    """Validate against the bytes, not against the header's claims."""
    if profile not in PROFILES:
        raise ValueError(f"unknown ISA profile: {profile!r}")
    if not module.well_formed:
        raise ValidationFailed(f"{module.name}: structural validation failed")
    if module.sections > MAX_SECTIONS:
        raise ValidationFailed(
            f"{module.name}: {module.sections} sections exceeds the {MAX_SECTIONS} limit")
    if module.size_bytes > MAX_BYTES:
        raise ValidationFailed(
            f"{module.name}: {module.size_bytes} bytes exceeds the {MAX_BYTES} limit")

    permitted = PROFILES[profile]
    # Used-but-undeclared is the dangerous direction: it slips past a header check.
    undeclared = module.used_features - module.declared_features
    if undeclared:
        raise ValidationFailed(
            f"{module.name}: uses undeclared features {sorted(undeclared)}")
    outside = module.used_features - permitted
    if outside:
        raise FeatureRefused(
            f"{module.name}: features outside the {profile!r} profile: {sorted(outside)}")

    unused = module.declared_features - module.used_features
    deterministic = not (module.used_features & NON_DETERMINISTIC)
    return {"schema": "PK_MODULE_VALIDATION/1", "module": module.name,
            "profile": profile, "valid": True,
            "used": sorted(module.used_features),
            "declared_unused": sorted(unused),
            "deterministic": deterministic}


class PortableComputeIsaComponent(Component):
    """Master-applied component for INV-09."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        core = frozenset({"core", "bulk-memory"})
        m = Module("svc", core, core)
        result = validate(m, profile="deterministic")
        assert result["valid"] and result["deterministic"]
        assert validate(m, profile="deterministic") == result
        findings[5] = self.satisfied(
            items[5],
            f"Validation is deterministic and reports the features actually used "
            f"({', '.join(result['used'])}) rather than the ones declared.",
            *self._evidence("component.py::validate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        sneaky = Module("sneaky", frozenset({"core"}), frozenset({"core", "threads"}))
        try:
            validate(sneaky, profile="permissive")
        except ValidationFailed:
            findings[6] = self.satisfied(
                items[6],
                "A module using a feature it did not declare fails validation even under the permissive "
                "profile, so a header check cannot be used to slip past the feature gate.",
                *self._evidence("component.py::validate"))
        simd = Module("simd", frozenset({"core", "simd"}), frozenset({"core", "simd"}))
        try:
            validate(simd, profile="deterministic")
        except FeatureRefused:
            findings[5] = self.satisfied(
                items[5],
                "A feature outside the environment's profile is refused; the profile is a ceiling, not a "
                "suggestion the module can argue with.",
                *self._evidence("component.py::PROFILES"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        risky = Module("risky", frozenset({"core", "threads"}), frozenset({"core", "threads"}))
        result = validate(risky, profile="permissive")
        assert result["valid"] and not result["deterministic"]
        findings[4] = self.satisfied(
            items[4],
            "The determinism class is computed from the features actually used: a threads-using module "
            "validates under the permissive profile but is reported non-deterministic, so replicas are "
            "never assumed to agree.",
            *self._evidence("component.py::NON_DETERMINISTIC"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        proven = []
        for label, m in [
            ("malformed", Module("a", frozenset(), frozenset(), well_formed=False)),
            ("section explosion", Module("b", frozenset(), frozenset(), sections=MAX_SECTIONS + 1)),
            ("oversize", Module("c", frozenset(), frozenset(), size_bytes=MAX_BYTES + 1)),
        ]:
            try:
                validate(m, profile="deterministic")
            except ValidationFailed:
                proven.append(label)
        assert len(proven) == 3
        findings[5] = self.satisfied(
            items[5],
            f"Resource limits are enforced at validation ({', '.join(proven)}), so a hostile module is "
            "rejected before it can consume engine resources.",
            *self._evidence("component.py::validate"))
        return findings

COMPONENT = PortableComputeIsaComponent
