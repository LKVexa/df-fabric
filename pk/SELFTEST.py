#!/usr/bin/env python3
"""Dependency-free conformance self-test.

Runs the same checks as ``tests/test_pk_components.py`` without requiring
pytest, so the suite is executable on an air-gapped host.  Exit code 0 means
every discovered component certified and the batch gate is not NO_GO.
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pk_core import (  # noqa: E402
    Checklist, ConformanceGate, Dimension, ElementId, EvidenceLedger,
    Registry, Status, WorkflowEngine,
)
from pk_core.integration import ownership  # noqa: E402
from pk_core.gate import NO_GO  # noqa: E402

FAILURES: list[str] = []
PASSED = 0


def check(label: str, fn) -> None:
    global PASSED
    try:
        fn()
    except Exception:
        FAILURES.append(f"{label}\n{traceback.format_exc(limit=3)}")
        print(f"  FAIL  {label}")
    else:
        PASSED += 1
        print(f"  ok    {label}")


def per_component(component) -> None:
    eid = component.element_id

    def contract():
        defects = component.contract.validate()
        assert not defects, f"contract defects: {defects}"
        assert component.contract.element == eid
        ElementId.parse(eid)
        owns = {s.lower() for s in component.contract.owns}
        assert not owns & {s.lower() for s in component.contract.not_owns}

    def checklist():
        assert len(component.checklist) == 100
        assert component.checklist.ids() == [component.element.check(n) for n in range(1, 101)]
        for dimension in Dimension:
            assert len(component.checklist.for_dimension(dimension)) == 10

    def master():
        # The 100 master prompts are carried by the project that OWNS the element.
        # A component installed here only as an integration dependency ships code
        # and its checklist, not the bulky prompt series.
        if eid not in OWNED:
            assert not component.master_prompt_path.exists(), (
                f"{eid} is not owned here but carries MASTER.md")
            return
        text = component.master_prompt_path.read_text(encoding="utf-8")
        assert eid in text
        assert text.count("## Master Prompt") == 100, "not all 100 master prompts are present"

    def assessment():
        findings = [f for fs in component.assess_all().values() for f in fs]
        assert len(findings) == 100
        assert {f.check_id for f in findings} == set(component.checklist.ids())
        blocked = [f.check_id for f in findings if f.status is Status.BLOCKED]
        assert not blocked, f"blocked requirements: {blocked}"
        for f in findings:
            if f.status is Status.PARTIAL:
                assert f.note.strip(), f"{f.check_id} is partial without a reason"
        repeat = [f.to_dict() for fs in component.assess_all().values() for f in fs]
        assert repeat == [f.to_dict() for f in findings], "assessment is not deterministic"

    def workflow():
        result = WorkflowEngine().run(component)
        failed = [s.stage.name for s in result.stages if not s.ok]
        assert result.certified, f"not certified; failed stages: {failed}"
        # Coverage below 1.0 is legitimate: a PARTIAL finding is an honestly
        # recorded gap, and the gate reports it as a condition, not a pass.
        assert result.coverage >= 0.9, f"coverage {result.coverage:.0%} is below the 90% floor"
        assert len(result.findings) == 100

    def w0_halts():
        broken = REGISTRY.get(eid)
        broken.contract.source_of_truth = ""
        result = WorkflowEngine().run(broken)
        assert not result.certified
        assert result.stages[0].stage.name == "W0" and not result.stages[0].ok

    def evidence():
        ledger = EvidenceLedger()
        WorkflowEngine(ledger).run(component)
        assert len(ledger) == 10, "expected one evidence record per stage"
        assert not ledger.verify()
        record = list(ledger)[3]
        object.__setattr__(record, "summary", record.summary + " (edited)")
        assert ledger.verify(), "a mutated record was not detected"

    def evidence_round_trip():
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            WorkflowEngine(EvidenceLedger(path)).run(component)
            reloaded = EvidenceLedger(path)
            assert len(reloaded) == 10 and not reloaded.verify()

    def blocked_is_no_go():
        class Broken(type(component)):
            def assess_operations(self, items):
                findings = super().assess_operations(items)
                findings[0] = self.blocked(items[0], "deliberately blocked for the negative test")
                return findings

        gate = ConformanceGate().evaluate([WorkflowEngine().run(Broken())])
        assert gate.verdict == NO_GO and gate.blockers

    def checklist_round_trip():
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CHECKLIST.json"
            component.checklist.save(path)
            assert Checklist.load(path).to_dict() == component.checklist.to_dict()

    for label, fn in [
        ("contract validates", contract),
        ("checklist is 100 contiguous items over ten dimensions", checklist),
        ("all 100 master prompts carried", master),
        ("all 100 requirements answered, none blocked, deterministic", assessment),
        ("W0-W9 workflow certifies", workflow),
        ("W0 halts on an incomplete contract", w0_halts),
        ("evidence chain is intact and tamper-evident", evidence),
        ("evidence persists and reloads", evidence_round_trip),
        ("a blocked requirement yields NO_GO", blocked_is_no_go),
        ("checklist round-trips through JSON", checklist_round_trip),
    ]:
        check(f"{eid}: {label}", fn)



def registry_completeness() -> None:
    """Every component package on disk must be discovered by the registry.

    A component package whose class accidentally shadows pk_core's Component --
    by defining a local class of the same name before the subclass statement --
    still imports cleanly but is silently invisible to discovery. This check
    turns that into a failure instead of a quietly missing element.
    """
    on_disk = {json.loads(p.read_text(encoding="utf-8"))["element"]
               for p in Path(__file__).resolve().parent.glob("pk_components/*/CHECKLIST.json")}
    discovered = set(REGISTRY.ids())
    missing = sorted(on_disk - discovered)
    assert not missing, f"component packages present but not discovered: {missing}"


REGISTRY = Registry().discover()
OWNED = ownership(Path(__file__).resolve().parent)


def main() -> int:
    if not len(REGISTRY):
        print("no components discovered under pk_components", file=sys.stderr)
        return 2
    print(f"pk self-test: {len(REGISTRY)} component(s)\n")
    for element_id in REGISTRY.ids():
        per_component(REGISTRY.get(element_id))

    def batch_gate():
        engine = WorkflowEngine(EvidenceLedger())
        results = [engine.run(c) for c in REGISTRY.instantiate()]
        gate = ConformanceGate().evaluate(results)
        assert gate.verdict != NO_GO, f"gate blockers: {gate.blockers}"
        assert len(gate.elements) == len(REGISTRY)
        json.dumps(gate.to_dict())

    check("every component package is discovered", registry_completeness)
    check("batch gate is not NO_GO", batch_gate)

    print(f"\n{PASSED} passed, {len(FAILURES)} failed")
    for failure in FAILURES:
        print("\n" + failure)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
