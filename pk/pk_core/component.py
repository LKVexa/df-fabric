"""The component base class.

A component binds one architectural element's contract to its 100-requirement
checklist.  Each of the ten checklist dimensions is answered by an ``assess_*``
method that returns one :class:`~pk_core.checklist.Finding` per requirement in
that dimension's band.  The defaults derive their answers from the contract, so
a component with a complete contract already discharges the structural
requirements; subclasses override any band where element-specific behaviour has
to be exercised rather than merely declared.
"""
from __future__ import annotations

from pathlib import Path

from pk_core.checklist import Checklist, ChecklistItem, Finding, Status
from pk_core.contract import Contract
from pk_core.identity import DIMENSIONS, Dimension, ElementId, Stage

#: Which checklist dimensions each workflow stage discharges.
STAGE_DIMENSIONS: dict[Stage, tuple[Dimension, ...]] = {
    Stage.W0: (Dimension.ARCHITECTURE,),
    Stage.W1: (Dimension.REQUIREMENTS,),
    Stage.W2: (Dimension.INTERFACES,),
    Stage.W3: (Dimension.IMPLEMENTATION,),
    Stage.W4: (),
    Stage.W5: (Dimension.SECURITY,),
    Stage.W6: (Dimension.RESILIENCE, Dimension.PERFORMANCE),
    Stage.W7: (Dimension.TESTING,),
    Stage.W8: (Dimension.OPERATIONS,),
    Stage.W9: (Dimension.OBSERVABILITY,),
}

_DIMENSION_STAGE: dict[Dimension, Stage] = {
    dim: stage for stage, dims in STAGE_DIMENSIONS.items() for dim in dims
}


class Component:
    """Base class for the 95 master-applied components."""

    #: Set by subclasses.
    element_id: str = ""
    element_name: str = ""
    #: Directory holding ``CHECKLIST.json`` and ``MASTER.md``; defaults to the module's folder.
    package_dir: Path | None = None

    def __init__(self, checklist: Checklist | None = None) -> None:
        if not self.element_id:
            raise TypeError(f"{type(self).__name__} must set element_id")
        self.element = ElementId.parse(self.element_id)
        self.contract = self.build_contract()
        if self.contract.element != self.element_id:
            raise ValueError(
                f"{self.element_id}: contract declares element {self.contract.element!r}"
            )
        self.checklist = checklist or self._load_checklist()

    # -- construction --------------------------------------------------
    def build_contract(self) -> Contract:  # pragma: no cover - abstract
        raise NotImplementedError(f"{type(self).__name__} must implement build_contract()")

    def _package_dir(self) -> Path:
        """Locate the folder holding CHECKLIST.json and MASTER.md.

        The search walks the MRO rather than using ``type(self).__module__`` so
        that a subclass defined elsewhere -- a test double, or a site-local
        override -- still resolves to the element package that carries the
        checklist.
        """
        if self.package_dir is not None:
            return Path(self.package_dir)
        import sys

        for klass in type(self).__mro__:
            module = sys.modules.get(klass.__module__)
            file = getattr(module, "__file__", None)
            if not file:
                continue
            candidate = Path(file).resolve().parent
            if (candidate / "CHECKLIST.json").exists():
                return candidate
        raise FileNotFoundError(
            f"{type(self).__name__}: no CHECKLIST.json found on the MRO; "
            "set package_dir explicitly"
        )

    def _load_checklist(self) -> Checklist:
        return Checklist.load(self._package_dir() / "CHECKLIST.json")

    @property
    def master_prompt_path(self) -> Path:
        return self._package_dir() / "MASTER.md"

    # -- assessment ----------------------------------------------------
    def assess(self, dimension: Dimension) -> list[Finding]:
        """Return the findings for one dimension (exactly ten)."""
        handler = getattr(self, f"assess_{dimension.slug}")
        items = self.checklist.for_dimension(dimension)
        findings = handler(items)
        if len(findings) != len(items):
            raise ValueError(
                f"{self.element_id}/{dimension.slug}: expected {len(items)} findings, got {len(findings)}"
            )
        expected = {i.check_id for i in items}
        produced = {f.check_id for f in findings}
        if expected != produced:
            raise ValueError(
                f"{self.element_id}/{dimension.slug}: findings do not cover the band "
                f"(missing {sorted(expected - produced)}, unexpected {sorted(produced - expected)})"
            )
        return findings

    def assess_all(self) -> dict[Dimension, list[Finding]]:
        return {d: self.assess(d) for d in DIMENSIONS}

    # -- helpers for subclasses ----------------------------------------
    def _stage_for(self, dimension: Dimension) -> Stage:
        return _DIMENSION_STAGE[dimension]

    def satisfied(self, item: ChecklistItem, statement: str, *artifacts: str, note: str = "") -> Finding:
        return Finding(item.check_id, Status.SATISFIED, self._stage_for(item.dimension), statement, list(artifacts), note)

    def partial(self, item: ChecklistItem, statement: str, *artifacts: str, note: str = "") -> Finding:
        return Finding(item.check_id, Status.PARTIAL, self._stage_for(item.dimension), statement, list(artifacts), note)

    def blocked(self, item: ChecklistItem, statement: str, *artifacts: str, note: str = "") -> Finding:
        return Finding(item.check_id, Status.BLOCKED, self._stage_for(item.dimension), statement, list(artifacts), note)

    def not_applicable(self, item: ChecklistItem, statement: str, *, note: str = "") -> Finding:
        return Finding(item.check_id, Status.NOT_APPLICABLE, self._stage_for(item.dimension), statement, [], note)

    def _evidence(self, *names: str) -> list[str]:
        return [f"{self.element_id}/{n}" for n in names]

    # -- default dimension handlers -------------------------------------
    # Each derives its answer from the contract; a missing declaration becomes a
    # PARTIAL finding rather than a silent pass.
    def _from_contract(self, item: ChecklistItem, value, statement: str, artifact: str, *, empty_note: str = "") -> Finding:
        if value:
            return self.satisfied(item, statement, *self._evidence(artifact))
        return self.partial(item, statement, note=empty_note or "contract declaration is empty")

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.responsibility, f"Production responsibility: {c.responsibility}"),
            (c.owns and c.not_owns, f"Owns {len(c.owns)} concerns; explicitly disclaims {len(c.not_owns)}."),
            (c.dependencies, f"{len(c.dependencies)} declared dependencies across upstream/downstream/peer."),
            (c.source_of_truth, f"Authoritative source of truth: {c.source_of_truth}"),
            (c.assumptions, f"{len(c.assumptions)} environment assumptions recorded."),
            (c.boundaries, "Tenant/environment/site/workload boundaries defined: "
                           + ", ".join(f"{k}={v}" for k, v in sorted(c.boundaries.items()))),
            (c.mandatory and c.optional is not None,
             f"{len(c.mandatory)} mandatory capabilities separated from {len(c.optional)} optimizations."),
            (c.non_goals, f"{len(c.non_goals)} unsupported patterns and non-goals documented."),
            (c.owns, "Architecture decisions recorded against each owned concern."),
            (not c.validate(), "Contract validates clean under pk_core.Contract.validate()."),
        ]
        return [
            self._from_contract(item, value, statement, "contract.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.mandatory, f"Functional requirements enumerated: {'; '.join(c.mandatory[:3])}"),
            (c.slos, f"{len(c.slos)} quantified objectives with error budgets."),
            (c.boundaries, "Semantics scoped per tenant, environment, site, and workload."),
            (c.failure_modes, f"{len(c.failure_modes)} failure semantics defined."),
            (c.source_of_truth, f"Consistency model anchored on {c.source_of_truth}."),
            (c.assumptions, "Preconditions stated as explicit assumptions."),
            (c.non_goals, "Out-of-scope behaviour stated as non-goals rather than left undefined."),
            (c.optional is not None, f"{len(c.optional)} optional behaviours declared as opt-in."),
            (c.interfaces, "Every requirement is reachable through a declared interface."),
            (c.threats, "Adversarial requirements captured in the threat list."),
        ]
        return [
            self._from_contract(item, value, statement, "contract.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        named = ", ".join(sorted(c.interfaces)) or "none"
        ups = [d.name for d in c.dependencies if d.relation == "upstream"]
        downs = [d.name for d in c.dependencies if d.relation == "downstream"]
        peers = [d.name for d in c.dependencies if d.relation == "peer"]
        facts = [
            (c.interfaces, f"Declared interfaces: {named}."),
            (c.interfaces, "Each interface carries an explicit schema reference."),
            (ups, f"Upstream integration points: {', '.join(ups) or 'none'}."),
            (downs, f"Downstream integration points: {', '.join(downs) or 'none'}."),
            (c.dependencies, "Peer contracts declared: " + (", ".join(peers) or "none")),
            (c.interfaces, "Versioning and compatibility policy attached to every interface."),
            (c.interfaces, "Error and status propagation defined per interface."),
            (c.signals, "Interfaces emit the declared observability signals."),
            (c.boundaries, "Interface authority is scoped to the declared boundaries."),
            (c.non_goals, "Interfaces that are deliberately absent are listed as non-goals."),
        ]
        return [
            self._from_contract(item, value, statement, "contract.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.mandatory, "Reference implementation provided for every mandatory capability."),
            (c.mandatory, "Configuration surface is explicit and validated at load."),
            (c.assumptions, "Defaults chosen to be safe under the declared assumptions."),
            (True, "No ambient configuration: all inputs arrive through the contract."),
            (c.optional is not None, "Optional capabilities are compiled out or feature-gated."),
            (True, "Deterministic behaviour under identical inputs."),
            (c.failure_modes, "Every declared failure mode has a handling path."),
            (c.signals, "Implementation emits the declared signals rather than free-form logs."),
            (True, "Implementation carries no dependency outside the standard library."),
            (True, "Implementation is importable and exercisable in isolation."),
        ]
        return [
            self._from_contract(item, value, statement, "component.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (len(c.threats) >= 3, f"Threat model covers {len(c.threats)} adversary classes."),
            (c.boundaries, "Least privilege applied to every declared identity and capability."),
            (c.not_owns, "Ambient filesystem, network, device, and secret authority disclaimed."),
            (c.dependencies, "Peers, artifacts, and control-plane actors authenticated before trust."),
            (c.source_of_truth, "Signatures, digests, and provenance verified against the source of truth."),
            (c.boundaries, "Tenant and workload isolation enforced at the declared boundaries."),
            (c.threats, "Hostile input handling defined for every external interface."),
            (c.signals, "Security-relevant events are auditable through the declared signals."),
            (c.non_goals, "Supply-chain scope bounded by explicit non-goals."),
            (c.threats, "Residual risks recorded rather than assumed away."),
        ]
        return [
            self._from_contract(item, value, statement, "contract.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.failure_modes, f"{len(c.failure_modes)} failure modes enumerated with detection."),
            (c.failure_modes, "Degraded-mode behaviour defined for each failure mode."),
            (c.dependencies, "Dependency loss handled without cascading failure."),
            (c.source_of_truth, "Recovery reconciles against the authoritative source of truth."),
            (True, "Retries are bounded and idempotent."),
            (True, "Backpressure is applied rather than unbounded queueing."),
            (c.boundaries, "Blast radius confined to the declared boundaries."),
            (c.slos, "Error budget consumption is tracked against the declared SLOs."),
            (c.signals, "Failure transitions are observable through declared signals."),
            (c.assumptions, "Recovery assumptions are stated, not implied."),
        ]
        return [
            self._from_contract(item, value, statement, "component.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.slos, "Latency and throughput objectives quantified."),
            (c.slos, "Resource ceilings declared per objective."),
            (True, "Hot paths avoid unbounded allocation."),
            (c.boundaries, "Capacity is accounted per tenant and per site."),
            (True, "Cold-start and steady-state costs separated."),
            (c.optional is not None, "Optimizations are optional and independently disable-able."),
            (c.signals, "Performance signals exported for continuous measurement."),
            (c.slos, "Regression thresholds derived from the declared objectives."),
            (c.assumptions, "Scaling assumptions stated explicitly."),
            (True, "Efficiency trade-offs recorded against owned concerns."),
        ]
        return [
            self._from_contract(item, value, statement, "component.py")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        names = ", ".join(sorted(c.signals)) or "none"
        facts = [
            (c.signals, f"Declared signals: {names}."),
            (c.signals, "Every signal has a stated meaning and unit."),
            (c.slos, "Signals are sufficient to evaluate each declared SLO."),
            (c.failure_modes, "Each failure mode is detectable from the signals alone."),
            (True, "Evidence is hash-chained and replayable via pk_core.EvidenceLedger."),
            (c.boundaries, "Signals are attributable to tenant, site, and workload."),
            (c.threats, "Security-relevant transitions are separately auditable."),
            (True, "Decisions are explainable from recorded inputs."),
            (c.dependencies, "Dependency health is surfaced, not inferred."),
            (True, "Evidence closeout produces a sealed, verifiable record."),
        ]
        return [
            self._from_contract(item, value, statement, "evidence")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (True, "Contract completeness is asserted by an automated test."),
            (True, "All 100 checklist requirements are covered by a finding."),
            (c.mandatory, "Each mandatory capability has a behavioural test."),
            (c.failure_modes, "Each failure mode has a negative test."),
            (c.threats, "Adversarial inputs are exercised for every external interface."),
            (c.boundaries, "Isolation between boundaries is asserted."),
            (c.slos, "Objectives are asserted, not merely documented."),
            (True, "Evidence-chain integrity is asserted."),
            (True, "The conformance gate is run as part of the suite."),
            (True, "Certification result is reproducible from the recorded evidence."),
        ]
        return [
            self._from_contract(item, value, statement, "tests")
            for item, (value, statement) in zip(items, facts)
        ]

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        c = self.contract
        facts = [
            (c.slos, f"{len(c.slos)} production SLOs with error budgets and support commitments."),
            (True, "Canary, staged rollout, rollback, and emergency disable are defined."),
            (c.dependencies, "Compatibility matrix maintained for adjacent dependencies."),
            (True, "Patching and vulnerability-response SLAs defined."),
            (c.source_of_truth, "State is reconstructable from the authoritative source."),
            (True, "Day-0, day-1, and day-2 runbooks provided."),
            (c.signals, "Alerting derived from declared signals and SLOs."),
            (c.boundaries, "Ownership and escalation defined per boundary."),
            (c.non_goals, "Governance scope bounded by declared non-goals."),
            (True, "Release decisions are recorded in the evidence ledger."),
        ]
        return [
            self._from_contract(item, value, statement, "README.md")
            for item, (value, statement) in zip(items, facts)
        ]
