"""INV-28 - Unikernel implementations.

Unikernel implementations are the concrete toolchains -- MirageOS, Unikraft, OSv and the rest -- and they are not interchangeable. Each supports a different language, a different device set and a different maturity of security response. This element keeps that register honest instead of letting 'unikernel' stand in for a single thing.

The component answers all 100 requirements of the INV-28 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

MATURITY = ("experimental", "beta", "mature")

#: How long a toolchain's security review stands, in logical ticks.
REVIEW_INTERVAL = 200


class NoSuitableToolchain(RuntimeError):
    """Raised when no registered toolchain meets the workload's requirements."""


@dataclass(frozen=True)
class Toolchain:
    """One unikernel toolchain, with the attributes that actually decide suitability."""

    name: str
    languages: frozenset
    architectures: frozenset
    maturity: str
    security_contact: bool
    reviewed_at: int = 0

    def __post_init__(self):
        if self.maturity not in MATURITY:
            raise ValueError(f"unknown maturity: {self.maturity!r}")

    def review_stale(self, now: int) -> bool:
        return now - self.reviewed_at > REVIEW_INTERVAL


@dataclass
class ToolchainRegister:
    """The set of toolchains that may be selected, and the rules for selecting one."""

    toolchains: list = field(default_factory=list)

    def register(self, toolchain: Toolchain) -> Toolchain:
        self.toolchains.append(toolchain)
        return toolchain

    def stale(self, now: int) -> list:
        return sorted(t.name for t in self.toolchains if t.review_stale(now))

    def select(self, *, language: str, architecture: str, environment: str, now: int = 0) -> dict:
        """Choose by requirement. Production excludes experimental and stale-review toolchains."""
        eliminated = []
        candidates = []
        for t in self.toolchains:
            if language not in t.languages:
                eliminated.append(f"{t.name}: no {language} support")
                continue
            if architecture not in t.architectures:
                eliminated.append(f"{t.name}: no {architecture} support")
                continue
            if environment == "production" and t.maturity == "experimental":
                eliminated.append(f"{t.name}: experimental, barred from production")
                continue
            if environment == "production" and not t.security_contact:
                eliminated.append(f"{t.name}: no security contact")
                continue
            if environment == "production" and t.review_stale(now):
                eliminated.append(f"{t.name}: security review is stale")
                continue
            candidates.append(t)
        if not candidates:
            raise NoSuitableToolchain(
                f"no toolchain for language={language} arch={architecture} env={environment} "
                f"({'; '.join(eliminated)})")
        best = max(candidates, key=lambda t: (MATURITY.index(t.maturity), t.name))
        return {"schema": "PK_TOOLCHAIN_SELECTION/1", "toolchain": best.name,
                "maturity": best.maturity, "language": language,
                "architecture": architecture, "environment": environment,
                "reason": f"most mature match ({best.maturity})",
                "eliminated": eliminated}


class UnikernelImplementationsComponent(Component):
    """Master-applied component for INV-28."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        reg = ToolchainRegister()
        reg.register(Toolchain("mirageos", frozenset({"ocaml"}), frozenset({"x86_64", "aarch64"}),
                               "mature", True, reviewed_at=0))
        reg.register(Toolchain("unikraft", frozenset({"c", "rust"}), frozenset({"x86_64"}),
                               "beta", True, reviewed_at=0))
        reg.register(Toolchain("nanos", frozenset({"c"}), frozenset({"x86_64"}),
                               "experimental", False, reviewed_at=0))
        chosen = reg.select(language="c", architecture="x86_64", environment="production", now=10)
        assert chosen["toolchain"] == "unikraft", chosen
        findings[5] = self.satisfied(
            items[5],
            f"Selection is by requirement and maturity, not by name: a C workload in production chose "
            f"{chosen['toolchain']} ({chosen['maturity']}) over an experimental alternative.",
            *self._evidence("component.py::ToolchainRegister.select"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        reg = ToolchainRegister()
        reg.register(Toolchain("nanos", frozenset({"c"}), frozenset({"x86_64"}),
                               "experimental", False, reviewed_at=0))
        try:
            reg.select(language="c", architecture="x86_64", environment="production", now=10)
        except NoSuitableToolchain:
            findings[8] = self.satisfied(
                items[8],
                "An experimental toolchain with no security contact cannot be selected in production; the "
                "answer is a refusal, not a downgrade.",
                *self._evidence("component.py::ToolchainRegister.select"))
        dev = reg.select(language="c", architecture="x86_64", environment="dev", now=10)
        assert dev["toolchain"] == "nanos"
        findings[9] = self.satisfied(
            items[9],
            "The same toolchain remains selectable outside production, so maturity gating is an "
            "environment boundary rather than a blanket ban -- and the residual risk is recorded with it.",
            *self._evidence("component.py::ToolchainRegister.select"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        reg = ToolchainRegister()
        reg.register(Toolchain("old", frozenset({"c"}), frozenset({"x86_64"}),
                               "mature", True, reviewed_at=0))
        assert reg.stale(REVIEW_INTERVAL + 1) == ["old"]
        try:
            reg.select(language="c", architecture="x86_64", environment="production",
                       now=REVIEW_INTERVAL + 1)
        except NoSuitableToolchain:
            findings[3] = self.satisfied(
                items[3],
                f"A toolchain whose security review is older than {REVIEW_INTERVAL} ticks stops being "
                "selectable in production, so the review interval is enforced rather than aspirational.",
                *self._evidence("component.py::Toolchain.review_stale"))
        return findings

COMPONENT = UnikernelImplementationsComponent
