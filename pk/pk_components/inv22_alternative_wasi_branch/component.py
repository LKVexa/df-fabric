"""INV-22 - Alternative WASI branch.

The alternative WASI branch exists because the standards track is not the only consumer of these interfaces, and a fork that ships earlier will accumulate divergence. This element's job is to know exactly where the branches differ, translate what can be translated, and refuse -- loudly -- what cannot, rather than letting a component silently behave differently on each.

The component answers all 100 requirements of the INV-22 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Per-interface classification between the standards branch and the fork.
#: IDENTICAL   - byte-for-byte the same; either branch will do.
#: SHIMMABLE   - different shape, same semantics; a translation is honest.
#: DIVERGENT   - different semantics; no shim can be correct.
IDENTICAL, SHIMMABLE, DIVERGENT = "identical", "shimmable", "divergent"

MATRIX = {
    "clocks": IDENTICAL,
    "random": IDENTICAL,
    "filesystem": SHIMMABLE,     # preopen encoding differs, confinement does not
    "sockets": DIVERGENT,        # the fork's addressing model is not the same model
    "threads": DIVERGENT,        # the fork exposes shared memory the branch does not have
}

BRANCHES = ("standards", "fork")


class Unclassified(KeyError):
    """Raised for an interface not in the matrix.  Unclassified is never compatible."""


class SemanticDivergence(RuntimeError):
    """Raised when a shim is requested for a semantically divergent interface."""


class UncertifiedBranch(RuntimeError):
    """Raised when a component is run on a branch it was not certified against."""


def classify(interface: str) -> str:
    if interface not in MATRIX:
        # Deliberately not a default of IDENTICAL: an interface nobody has
        # compared is the most likely place for divergence to hide.
        raise Unclassified(interface)
    return MATRIX[interface]


def shim(interface: str, value, frm: str, to: str):
    """Translate a value between branches, or refuse."""
    if frm not in BRANCHES or to not in BRANCHES:
        raise ValueError(f"unknown branch: {frm} -> {to}")
    kind = classify(interface)
    if kind == DIVERGENT:
        raise SemanticDivergence(
            f"{interface} has different semantics on each branch; no shim can be correct")
    if kind == IDENTICAL:
        return value
    return {"branch": to, "interface": interface, "value": value}


@dataclass
class Certification:
    """Which branch a component was certified against, and enforcement of it."""

    component: str
    branch: str
    uncertified_runs: int = 0

    def run_on(self, branch: str) -> str:
        if branch != self.branch:
            self.uncertified_runs += 1
            raise UncertifiedBranch(
                f"{self.component} is certified for '{self.branch}', not '{branch}'")
        return "ok"


@dataclass
class DriftReport:
    """Divergence measured per release, so growth is a number and not a feeling."""

    releases: dict = field(default_factory=dict)

    def record(self, release: str, matrix: dict) -> int:
        n = sum(1 for k in matrix.values() if k == DIVERGENT)
        self.releases[release] = n
        return n

    def growing(self) -> bool:
        counts = [self.releases[k] for k in sorted(self.releases)]
        return len(counts) > 1 and counts[-1] > counts[0]


class AlternativeWasiBranchComponent(Component):
    """Master-applied component for INV-22."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        assert shim("clocks", 5, "standards", "fork") == 5
        assert shim("filesystem", "/data", "standards", "fork")["branch"] == "fork"
        refused = False
        try:
            shim("sockets", None, "standards", "fork")
        except SemanticDivergence:
            refused = True
        unknown = False
        try:
            classify("some-new-interface")
        except Unclassified:
            unknown = True
        assert refused and unknown
        counts = {k: sum(1 for v in MATRIX.values() if v == k)
                  for k in (IDENTICAL, SHIMMABLE, DIVERGENT)}
        findings[0] = self.satisfied(
            items[0],
            f"Every interface carries an explicit classification ({counts}); identical ones pass through, "
            "shimmable ones translate, divergent ones refuse, and an interface nobody has compared raises "
            "rather than defaulting to compatible.",
            *self._evidence("component.py::MATRIX", "component.py::shim"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        cert = Certification("edge-handler", "standards")
        assert cert.run_on("standards") == "ok"
        blocked = False
        try:
            cert.run_on("fork")
        except UncertifiedBranch:
            blocked = True
        assert blocked and cert.uncertified_runs == 1
        findings[1] = self.satisfied(
            items[1],
            "A component records the branch it was certified against and is refused on any other, so a "
            "deployment cannot quietly move a workload onto semantics it was never tested under.",
            *self._evidence("component.py::Certification.run_on"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        drift = DriftReport()
        drift.record("v1", {"clocks": IDENTICAL})
        now = drift.record("v2", MATRIX)
        assert drift.growing() and now == 2
        findings[1] = self.satisfied(
            items[1],
            f"Divergence is counted per release (v1: 0, v2: {now}) and growth is reported as a boolean the "
            "owner can act on, so the branches drifting apart is a measured fact rather than something "
            "discovered when a workload misbehaves.",
            *self._evidence("component.py::DriftReport"))
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        classified = 0
        for interface in MATRIX:
            classify(interface)
            classified += 1
        assert classified == len(MATRIX)
        findings[0] = self.satisfied(
            items[0],
            f"All {classified} matrix entries resolve to a classification and each classification path "
            "(pass-through, shim, refusal, unclassified) is exercised, so the matrix is tested rather "
            "than merely written down.",
            *self._evidence("component.py::classify", "component.py::MATRIX"))
        return findings

COMPONENT = AlternativeWasiBranchComponent
