"""INV-34 - Legacy CPU expansion path.

The legacy CPU expansion path is the unglamorous truth of edge estates: hardware from several generations runs side by side, and a workload built for the newest instruction set will fault on the oldest node. This element defines the baseline everything must run on and makes any step above it an explicit, checked requirement.

The component answers all 100 requirements of the INV-34 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Cumulative x86-64 feature levels. Each level includes everything below it.
LEVELS = {
    "v1": frozenset({"sse2"}),
    "v2": frozenset({"sse2", "sse4_2", "popcnt"}),
    "v3": frozenset({"sse2", "sse4_2", "popcnt", "avx", "avx2", "bmi2"}),
    "v4": frozenset({"sse2", "sse4_2", "popcnt", "avx", "avx2", "bmi2", "avx512f"}),
}
LEVEL_ORDER = ("v1", "v2", "v3", "v4")

#: The estate baseline: nothing below this is admitted at all.
BASELINE = "v2"


class BelowBaseline(RuntimeError):
    """Raised when a node does not even meet the estate baseline."""


class LevelUnsatisfied(RuntimeError):
    """Raised when a node cannot provide the feature level a workload requires."""


@dataclass
class Cpu:
    """One node's CPU, as reported and as usable after mitigation masking."""

    node: str
    reported: frozenset
    masked: frozenset = frozenset()      # physically present but unusable under mitigation

    @property
    def usable(self) -> frozenset:
        """A mitigation-masked feature is absent for every purpose."""
        return self.reported - self.masked

    def level(self) -> str:
        """The highest cumulative level this CPU fully satisfies."""
        best = None
        for name in LEVEL_ORDER:
            if LEVELS[name] <= self.usable:
                best = name
            else:
                break
        if best is None:
            raise BelowBaseline(f"{self.node}: does not satisfy even {LEVEL_ORDER[0]}")
        return best

    def meets_baseline(self) -> bool:
        try:
            return LEVEL_ORDER.index(self.level()) >= LEVEL_ORDER.index(BASELINE)
        except BelowBaseline:
            return False

    def mask_for_guest(self, requested_level: str) -> dict:
        """Never present more than the host actually provides."""
        if requested_level not in LEVELS:
            raise ValueError(f"unknown feature level: {requested_level!r}")
        available = LEVELS[requested_level] & self.usable
        withheld = sorted(LEVELS[requested_level] - self.usable)
        return {"schema": "PK_CPU_MASK/1", "node": self.node,
                "requested_level": requested_level,
                "exposed": sorted(available), "withheld": withheld,
                "satisfies_level": not withheld}


def match(cpu: Cpu, required_level: str) -> dict:
    if not cpu.meets_baseline():
        raise BelowBaseline(f"{cpu.node}: below the {BASELINE} estate baseline")
    mask = cpu.mask_for_guest(required_level)
    if not mask["satisfies_level"]:
        raise LevelUnsatisfied(
            f"{cpu.node} is {cpu.level()}, workload needs {required_level} "
            f"(missing {mask['withheld']})")
    return {"schema": "PK_CPU_MATCH/1", "node": cpu.node, "node_level": cpu.level(),
            "required_level": required_level, "satisfied": True}


class LegacyCpuExpansionPathComponent(Component):
    """Master-applied component for INV-34."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        modern = Cpu("n1", LEVELS["v3"])
        old = Cpu("n2", LEVELS["v2"])
        assert modern.level() == "v3" and old.level() == "v2"
        assert match(modern, "v3")["satisfied"]
        assert match(old, "v2")["satisfied"]
        findings[5] = self.satisfied(
            items[5],
            f"Levels are cumulative and derived from the reported feature set: {modern.node} is "
            f"{modern.level()}, {old.node} is {old.level()}, and both meet the {BASELINE} baseline.",
            *self._evidence("component.py::Cpu.level"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[4] = self.satisfied(
            items[4],
            f"The estate is assumed heterogeneous: {len(LEVEL_ORDER)} feature levels are defined with "
            f"{BASELINE} as the floor, so a mixed-generation fleet is the design point rather than an "
            "exception to be handled later.",
            *self._evidence("component.py::LEVELS", "contract.py"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        masked = Cpu("n1", LEVELS["v3"], masked=frozenset({"avx2"}))
        result = masked.mask_for_guest("v3")
        assert not result["satisfies_level"] and result["withheld"] == ["avx2"]
        assert "avx2" not in result["exposed"]
        findings[2] = self.satisfied(
            items[2],
            "A feature masked by a mitigation is withheld from the guest even though the CPU still reports "
            "it, so a guest never negotiates a capability the host cannot honour.",
            *self._evidence("component.py::Cpu.mask_for_guest"))
        try:
            match(masked, "v3")
        except LevelUnsatisfied:
            findings[5] = self.satisfied(
                items[5],
                f"The same masking drops the node from v3 to {masked.level()} for placement purposes, so a "
                "v3 workload is refused rather than placed where it would fault.",
                *self._evidence("component.py::match"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        ancient = Cpu("n3", LEVELS["v1"])
        assert not ancient.meets_baseline()
        try:
            match(ancient, "v2")
        except BelowBaseline:
            findings[0] = self.satisfied(
                items[0],
                f"A node below the {BASELINE} baseline is refused outright rather than being offered "
                "workloads it cannot run.",
                *self._evidence("component.py::Cpu.meets_baseline"))
        try:
            Cpu("n4", frozenset()).level()
        except BelowBaseline:
            findings[1] = self.satisfied(
                items[1],
                "A CPU satisfying no level at all raises rather than defaulting to the lowest, so an "
                "unrecognised node never silently becomes v1.",
                *self._evidence("component.py::Cpu.level"))
        return findings

COMPONENT = LegacyCpuExpansionPathComponent
