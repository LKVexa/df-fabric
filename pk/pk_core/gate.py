"""Conformance gate: turns workflow results into a GO / CONDITIONAL_GO / NO_GO verdict."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pk_core.checklist import Status
from pk_core.workflow import WorkflowResult

GO = "GO"
CONDITIONAL_GO = "CONDITIONAL_GO"
NO_GO = "NO_GO"


@dataclass
class GateResult:
    verdict: str
    generated_at: str
    elements: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema": "PK_GATE_RESULTS/1",
            "verdict": self.verdict,
            "generated_at": self.generated_at,
            "element_count": len(self.elements),
            "blockers": self.blockers,
            "conditions": self.conditions,
            "elements": self.elements,
        }


class ConformanceGate:
    """Evaluates one or more workflow results against the release policy.

    Policy: any blocked requirement or uncertified element is a blocker; any
    partial requirement is a condition.  Blockers yield NO_GO, conditions alone
    yield CONDITIONAL_GO, and a clean sweep yields GO.
    """

    def __init__(self, *, clock=None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(self, results: list[WorkflowResult]) -> GateResult:
        elements: list[dict] = []
        blockers: list[str] = []
        conditions: list[str] = []

        for result in results:
            blocked = [f.check_id for f in result.findings if f.status is Status.BLOCKED]
            partial = [f.check_id for f in result.findings if f.status is Status.PARTIAL]
            failed_stages = [s.stage.name for s in result.stages if not s.ok]

            if blocked:
                blockers.append(f"{result.element}: {len(blocked)} blocked requirements ({', '.join(blocked[:5])})")
            if failed_stages:
                blockers.append(f"{result.element}: stages not passed ({', '.join(failed_stages)})")
            if partial:
                conditions.append(f"{result.element}: {len(partial)} partial requirements ({', '.join(partial[:5])})")

            elements.append(
                {
                    "element": result.element,
                    "name": result.name,
                    "certified": result.certified,
                    "coverage": round(result.coverage, 4),
                    "counts": result.counts,
                    "failed_stages": failed_stages,
                    "evidence_head": result.evidence_head,
                }
            )

        if blockers:
            verdict = NO_GO
        elif conditions:
            verdict = CONDITIONAL_GO
        else:
            verdict = GO
        return GateResult(verdict, self._clock().isoformat(), elements, blockers, conditions)
