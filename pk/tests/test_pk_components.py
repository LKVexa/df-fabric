"""Conformance suite for the master-applied components.

Every test here is derived from the Testing & Certification dimension of the
Post-Kubernetes Master Prompt & Workflow Series: the contract must validate, all
100 requirements of every element must be answered, the evidence chain must be
tamper-evident, and the conformance gate must be reproducible.
"""
from __future__ import annotations

import json

import pytest

from pk_core import (
    Checklist, ConformanceGate, Dimension, ElementId, EvidenceLedger,
    Registry, Status, WorkflowEngine,
)
from pk_core.gate import NO_GO

from pathlib import Path

from pk_core.integration import ownership

REGISTRY = Registry().discover()
ELEMENT_IDS = REGISTRY.ids()
OWNED = ownership(Path(__file__).resolve().parent.parent)


def test_registry_is_not_empty():
    assert ELEMENT_IDS, "no components discovered under pk_components"


@pytest.fixture(scope="module", params=ELEMENT_IDS)
def component(request):
    return REGISTRY.get(request.param)


# -- contract -------------------------------------------------------------
def test_contract_validates(component):
    defects = component.contract.validate()
    assert not defects, f"{component.element_id} contract defects: {defects}"


def test_contract_declares_its_own_element(component):
    assert component.contract.element == component.element_id
    ElementId.parse(component.element_id)


def test_owns_and_not_owns_are_disjoint(component):
    owns = {s.lower() for s in component.contract.owns}
    assert not owns & {s.lower() for s in component.contract.not_owns}


# -- checklist ------------------------------------------------------------
def test_checklist_has_100_contiguous_items(component):
    assert len(component.checklist) == 100
    assert component.checklist.ids() == [component.element.check(n) for n in range(1, 101)]


def test_every_dimension_owns_ten_requirements(component):
    for dimension in Dimension:
        assert len(component.checklist.for_dimension(dimension)) == 10


def test_master_prompt_is_carried(component):
    """The 100 master prompts ship with the project that owns the element.

    A component installed here only as an integration dependency carries its
    code and checklist but not the prompt series.
    """
    if component.element_id not in OWNED:
        assert not component.master_prompt_path.exists()
        return
    text = component.master_prompt_path.read_text(encoding="utf-8")
    assert component.element_id in text
    assert text.count("## Master Prompt") == 100, "not all 100 master prompts are present"


# -- assessment -----------------------------------------------------------
def test_all_100_requirements_are_answered(component):
    findings = [f for fs in component.assess_all().values() for f in fs]
    assert len(findings) == 100
    assert {f.check_id for f in findings} == set(component.checklist.ids())


def test_no_requirement_is_left_blocked(component):
    findings = [f for fs in component.assess_all().values() for f in fs]
    blocked = [f.check_id for f in findings if f.status is Status.BLOCKED]
    assert not blocked, f"{component.element_id} has blocked requirements: {blocked}"


def test_partial_findings_carry_a_reason(component):
    for fs in component.assess_all().values():
        for finding in fs:
            if finding.status is Status.PARTIAL:
                assert finding.note.strip(), f"{finding.check_id} is partial without a recorded reason"


def test_assessment_is_deterministic(component):
    first = [f.to_dict() for fs in component.assess_all().values() for f in fs]
    second = [f.to_dict() for fs in component.assess_all().values() for f in fs]
    assert first == second


# -- workflow -------------------------------------------------------------
def test_workflow_certifies(component):
    result = WorkflowEngine().run(component)
    failed = [s.stage.name for s in result.stages if not s.ok]
    assert result.certified, f"{component.element_id} not certified; failed stages: {failed}"
    # A PARTIAL finding is an honestly recorded gap, surfaced by the gate as a
    # condition, so full coverage is not required -- but a floor is.
    assert result.coverage >= 0.9, f"coverage {result.coverage:.0%} is below the 90% floor"
    assert len(result.findings) == 100


def test_workflow_halts_on_an_incomplete_contract(component):
    broken = REGISTRY.get(component.element_id)
    broken.contract.source_of_truth = ""
    result = WorkflowEngine().run(broken)
    assert not result.certified
    assert result.stages[0].stage.name == "W0" and not result.stages[0].ok


# -- evidence -------------------------------------------------------------
def test_evidence_chain_is_intact_and_tamper_evident(component):
    ledger = EvidenceLedger()
    WorkflowEngine(ledger).run(component)
    assert len(ledger) == 10, "expected one evidence record per workflow stage"
    assert not ledger.verify()
    record = list(ledger)[3]
    object.__setattr__(record, "summary", record.summary + " (edited)")
    assert ledger.verify(), "a mutated record was not detected"


def test_evidence_persists_and_reloads(component, tmp_path):
    path = tmp_path / "evidence.jsonl"
    WorkflowEngine(EvidenceLedger(path)).run(component)
    reloaded = EvidenceLedger(path)
    assert len(reloaded) == 10 and not reloaded.verify()


# -- gate -----------------------------------------------------------------
def test_gate_over_the_whole_batch_is_not_no_go():
    engine = WorkflowEngine(EvidenceLedger())
    results = [engine.run(c) for c in REGISTRY.instantiate()]
    gate = ConformanceGate().evaluate(results)
    assert gate.verdict != NO_GO, f"gate blockers: {gate.blockers}"
    assert len(gate.elements) == len(ELEMENT_IDS)
    json.dumps(gate.to_dict())  # the gate result must be serialisable


def test_gate_reports_a_blocked_requirement_as_no_go(component):
    class Broken(type(component)):
        def assess_operations(self, items):
            findings = super().assess_operations(items)
            findings[0] = self.blocked(items[0], "deliberately blocked for the negative test")
            return findings

    result = WorkflowEngine().run(Broken())
    gate = ConformanceGate().evaluate([result])
    assert gate.verdict == NO_GO and gate.blockers


# -- checklist round trip -------------------------------------------------
def test_checklist_round_trips(component, tmp_path):
    path = tmp_path / "CHECKLIST.json"
    component.checklist.save(path)
    assert Checklist.load(path).to_dict() == component.checklist.to_dict()


def test_every_component_package_is_discovered():
    """A package that shadows pk_core.Component imports fine but vanishes from discovery.

    Comparing what is on disk against what the registry found turns that silent
    disappearance into a test failure.
    """
    on_disk = {json.loads(p.read_text(encoding="utf-8"))["element"]
               for p in Path(__file__).resolve().parent.parent.glob("pk_components/*/CHECKLIST.json")}
    missing = sorted(on_disk - set(ELEMENT_IDS))
    assert not missing, f"component packages present but not discovered: {missing}"
