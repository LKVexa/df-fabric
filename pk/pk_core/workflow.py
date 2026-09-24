"""The W0-W9 workflow engine.

Running a component walks the ten stages in order.  Each stage discharges the
checklist dimensions mapped to it, records its findings in the evidence ledger,
and may halt the run: W0 refuses to proceed on an incomplete contract, and W7
refuses to certify when any requirement is blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pk_core.checklist import Finding, Status
from pk_core.component import STAGE_DIMENSIONS, Component
from pk_core.evidence import EvidenceLedger
from pk_core.identity import DIMENSIONS, Stage


@dataclass
class StageResult:
    stage: Stage
    ok: bool
    summary: str
    findings: list[Finding] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.name,
            "title": self.stage.title,
            "ok": self.ok,
            "summary": self.summary,
            "defects": self.defects,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class WorkflowResult:
    element: str
    name: str
    certified: bool
    stages: list[StageResult]
    findings: list[Finding]
    evidence_head: str

    @property
    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in Status}
        for f in self.findings:
            out[f.status.value] += 1
        return out

    @property
    def coverage(self) -> float:
        passing = sum(1 for f in self.findings if f.status.passing)
        return passing / len(self.findings) if self.findings else 0.0

    def to_dict(self) -> dict:
        return {
            "element": self.element,
            "name": self.name,
            "certified": self.certified,
            "counts": self.counts,
            "coverage": round(self.coverage, 4),
            "evidence_head": self.evidence_head,
            "stages": [s.to_dict() for s in self.stages],
        }


class WorkflowEngine:
    """Applies the ten workflow stages to a component."""

    def __init__(self, ledger: EvidenceLedger | None = None) -> None:
        # NB: an empty ledger is falsy (it defines __len__), so this must be an
        # identity check -- ``ledger or EvidenceLedger()`` would silently discard
        # the caller's ledger and drop every evidence record on the floor.
        self.ledger = EvidenceLedger() if ledger is None else ledger

    def run(self, component: Component) -> WorkflowResult:
        stages: list[StageResult] = []
        findings: list[Finding] = []
        halted = False

        for stage in Stage:
            if halted:
                stages.append(StageResult(stage, False, "not reached: an earlier stage halted the run"))
                continue
            result = self._run_stage(component, stage, findings)
            stages.append(result)
            findings.extend(result.findings)
            self.ledger.append(
                element=component.element_id,
                stage=stage.name,
                summary=result.summary,
                payload=result.to_dict(),
            )
            if not result.ok and stage in (Stage.W0, Stage.W7):
                halted = True

        certified = all(s.ok for s in stages) and len(findings) == len(component.checklist)
        return WorkflowResult(
            element=component.element_id,
            name=component.element_name or component.checklist.name,
            certified=certified,
            stages=stages,
            findings=findings,
            evidence_head=self.ledger.head,
        )

    # -- stages --------------------------------------------------------
    def _run_stage(self, component: Component, stage: Stage, so_far: list[Finding]) -> StageResult:
        dims = STAGE_DIMENSIONS[stage]
        produced: list[Finding] = []
        defects: list[str] = []

        if stage is Stage.W0:
            defects = component.contract.validate()
            if defects:
                return StageResult(stage, False, f"context lock refused: {len(defects)} contract defects", [], defects)

        for dim in dims:
            produced.extend(component.assess(dim))

        if stage is Stage.W4:
            defects = self._integration_defects(component)
            summary = "integration wiring verified" if not defects else f"{len(defects)} integration defects"
            return StageResult(stage, not defects, summary, [], defects)

        if stage is Stage.W7:
            blocked = [f.check_id for f in so_far + produced if f.status is Status.BLOCKED]
            if blocked:
                defects = [f"blocked requirement: {b}" for b in blocked]
                return StageResult(stage, False, f"certification refused: {len(blocked)} blocked requirements", produced, defects)

        if stage is Stage.W9:
            defects = self.ledger.verify()
            if defects:
                return StageResult(stage, False, "evidence chain is not intact", produced, defects)
            covered = {f.check_id for f in so_far + produced}
            missing = [i.check_id for i in component.checklist if i.check_id not in covered]
            if missing:
                defects = [f"uncovered requirement: {m}" for m in missing]
                return StageResult(stage, False, f"{len(missing)} requirements never answered", produced, defects)

        label = ", ".join(d.value for d in dims) or "no checklist dimension"
        return StageResult(stage, True, f"{stage.title}: {label} ({len(produced)} findings)", produced, [])

    @staticmethod
    def _integration_defects(component: Component) -> list[str]:
        c = component.contract
        defects: list[str] = []
        if not c.interfaces:
            defects.append("no interfaces declared to integrate")
        for dep in c.dependencies:
            if dep.required and not dep.why.strip():
                defects.append(f"required dependency {dep.name!r} has no stated reason")
        for name, schema in c.interfaces.items():
            if not schema.strip():
                defects.append(f"interface {name!r} has no schema reference")
        return defects


def run_all(components, ledger: EvidenceLedger | None = None) -> list[WorkflowResult]:
    engine = WorkflowEngine(ledger)
    return [engine.run(c) for c in components]
