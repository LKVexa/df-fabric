"""GAP-15 - Runtime compatibility certification.

Runtime compatibility certification answers the question a heterogeneous edge estate asks constantly: will this artifact actually run on that node? It certifies against a declared matrix and refuses to guess, because an untested pair is not a supported pair.

The component answers all 100 requirements of the GAP-15 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

CERTIFIED, INCOMPATIBLE, UNTESTED, EXPIRED, END_OF_LIFE = (
    "certified", "incompatible", "untested", "expired", "end-of-life")

#: How long a certification stands before re-testing is required.
CERTIFICATION_TTL = 500

SUPPORTED, DEPRECATED, EOL = "supported", "deprecated", "end-of-life"


@dataclass(frozen=True)
class Triple:
    """The unit of certification: one artifact on one runtime on one node profile."""

    artifact: str
    runtime: str
    profile: str


@dataclass
class CompatibilityMatrix:
    """A deliberately sparse matrix: an untested triple is uncertified, never inferred."""

    environment: str
    #: Triple -> (compatible: bool, tested_at: int)
    results: dict = field(default_factory=dict)
    #: runtime version -> lifecycle state
    lifecycle: dict = field(default_factory=dict)

    def record(self, triple: Triple, *, compatible: bool, at: int) -> None:
        """Record a real test result. This is the only way a triple becomes certifiable."""
        self.results[triple] = (compatible, at)

    def set_lifecycle(self, runtime: str, state: str) -> None:
        if state not in (SUPPORTED, DEPRECATED, EOL):
            raise ValueError(f"unknown lifecycle state: {state!r}")
        self.lifecycle[runtime] = state

    def certify(self, triple: Triple, now: int) -> dict:
        """Return a verdict. Untested and incompatible are different answers."""
        state = self.lifecycle.get(triple.runtime, SUPPORTED)
        if state == EOL:
            return {"schema": "PK_CERTIFICATION/1", "verdict": END_OF_LIFE,
                    "triple": vars(triple) if hasattr(triple, "__dict__") else triple._asdict()
                    if hasattr(triple, "_asdict") else str(triple),
                    "reason": f"runtime {triple.runtime} is end-of-life",
                    "deployable": False, "deprecated": True}

        record = self.results.get(triple)
        if record is None:
            return {"schema": "PK_CERTIFICATION/1", "verdict": UNTESTED,
                    "triple": str(triple),
                    "reason": "no recorded test result for this triple; compatibility is not inferred",
                    "deployable": False, "deprecated": state == DEPRECATED}

        compatible, tested_at = record
        if not compatible:
            return {"schema": "PK_CERTIFICATION/1", "verdict": INCOMPATIBLE,
                    "triple": str(triple),
                    "reason": f"tested at {tested_at} and found incompatible",
                    "deployable": False, "deprecated": state == DEPRECATED}
        if now - tested_at > CERTIFICATION_TTL:
            return {"schema": "PK_CERTIFICATION/1", "verdict": EXPIRED,
                    "triple": str(triple),
                    "reason": f"certified at {tested_at}, older than {CERTIFICATION_TTL}",
                    "deployable": False, "deprecated": state == DEPRECATED}
        return {"schema": "PK_CERTIFICATION/1", "verdict": CERTIFIED,
                "triple": str(triple), "reason": f"tested compatible at {tested_at}",
                "deployable": True, "deprecated": state == DEPRECATED,
                "age": now - tested_at}

    def coverage(self, requested: list) -> float:
        if not requested:
            return 1.0
        return sum(1 for t in requested if t in self.results) / len(requested)


class RuntimeCompatibilityCertificationComponent(Component):
    """Master-applied component for GAP-15."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        m = CompatibilityMatrix("prod")
        good = Triple("svc:1", "wasmtime-21", "arm64-sev")
        bad = Triple("svc:1", "wasmtime-20", "arm64-sev")
        m.record(good, compatible=True, at=0)
        m.record(bad, compatible=False, at=0)
        assert m.certify(good, now=1)["verdict"] == CERTIFIED
        assert m.certify(bad, now=1)["verdict"] == INCOMPATIBLE
        findings[5] = self.satisfied(
            items[5],
            "Certification reads directly from recorded test results, so a certified and an incompatible "
            "triple are both answered from evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        m = CompatibilityMatrix("prod")
        m.record(Triple("svc:1", "wasmtime-21", "arm64-sev"), compatible=True, at=0)
        near = m.certify(Triple("svc:1", "wasmtime-21", "arm64-tdx"), now=1)
        assert near["verdict"] == UNTESTED and not near["deployable"]
        findings[6] = self.satisfied(
            items[6],
            "A neighbouring profile that differs only in its isolation primitive returns untested rather "
            "than inheriting the certified verdict: similarity is never evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"))
        assert m.coverage([Triple("svc:1", "wasmtime-21", "arm64-sev"),
                           Triple("svc:1", "wasmtime-21", "arm64-tdx")]) == 0.5
        findings[1] = self.satisfied(
            items[1],
            "Matrix coverage is measurable (0.5 over a two-triple request), so the sparseness of the "
            "matrix is a reported quantity rather than a hidden assumption.",
            *self._evidence("component.py::CompatibilityMatrix.coverage"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        m = CompatibilityMatrix("prod")
        t = Triple("svc:1", "wasmtime-21", "arm64-sev")
        m.record(t, compatible=True, at=0)
        assert m.certify(t, now=CERTIFICATION_TTL)["verdict"] == CERTIFIED
        expired = m.certify(t, now=CERTIFICATION_TTL + 1)
        assert expired["verdict"] == EXPIRED and not expired["deployable"]
        findings[3] = self.satisfied(
            items[3],
            f"A certification expires {CERTIFICATION_TTL} ticks after its test and stops being deployable, "
            "so a stale result cannot carry a rollout.",
            *self._evidence("component.py::CompatibilityMatrix.certify"))
        m.set_lifecycle("wasmtime-21", EOL)
        eol = m.certify(t, now=1)
        assert eol["verdict"] == END_OF_LIFE and not eol["deployable"]
        findings[1] = self.satisfied(
            items[1],
            "An end-of-life runtime overrides even a fresh passing test result, so an unsupported runtime "
            "cannot stay in service on the strength of old evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"))
        return findings

COMPONENT = RuntimeCompatibilityCertificationComponent
