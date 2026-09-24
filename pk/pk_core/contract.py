"""The binding contract every component declares before it may run.

The contract is the machine-readable form of the Architecture & Scope and
Requirements & Semantics dimensions: what the element owns, what it refuses to
own, what it depends on, and what it promises.  ``validate`` is deliberately
strict -- a component with an incomplete contract cannot pass W0.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Dependency:
    """A named upstream, downstream, or peer relationship."""

    name: str
    relation: str  # "upstream" | "downstream" | "peer"
    why: str
    required: bool = True

    def __post_init__(self) -> None:
        if self.relation not in ("upstream", "downstream", "peer"):
            raise ValueError(f"unknown relation: {self.relation!r}")


@dataclass(frozen=True)
class Slo:
    """A production service-level objective with an error budget."""

    name: str
    objective: str
    error_budget: str


@dataclass
class Contract:
    """Binding declaration of an element's production responsibility."""

    element: str
    name: str
    responsibility: str
    owns: list[str] = field(default_factory=list)
    not_owns: list[str] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    source_of_truth: str = ""
    assumptions: list[str] = field(default_factory=list)
    boundaries: dict[str, str] = field(default_factory=dict)
    mandatory: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    interfaces: dict[str, str] = field(default_factory=dict)
    threats: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    slos: list[Slo] = field(default_factory=list)
    signals: dict[str, str] = field(default_factory=dict)

    # -- validation ---------------------------------------------------
    REQUIRED_BOUNDARIES = ("tenant", "environment", "site", "workload")

    def validate(self) -> list[str]:
        """Return a list of contract defects; empty means the contract is complete."""
        defects: list[str] = []

        def need(value, label: str, minimum: int = 1) -> None:
            if len(value) < minimum:
                defects.append(f"{label}: expected at least {minimum} entr{'y' if minimum == 1 else 'ies'}")

        if not self.responsibility.strip():
            defects.append("responsibility: must state the exact production responsibility")
        if not self.source_of_truth.strip():
            defects.append("source_of_truth: must name the authoritative source")
        need(self.owns, "owns")
        need(self.not_owns, "not_owns")
        need(self.dependencies, "dependencies")
        need(self.assumptions, "assumptions", 2)
        need(self.mandatory, "mandatory")
        need(self.non_goals, "non_goals")
        need(self.interfaces, "interfaces")
        need(self.threats, "threats", 3)
        need(self.failure_modes, "failure_modes", 2)
        need(self.slos, "slos")
        need(self.signals, "signals", 3)

        missing = [b for b in self.REQUIRED_BOUNDARIES if b not in self.boundaries]
        if missing:
            defects.append(f"boundaries: missing {', '.join(missing)}")

        overlap = sorted(set(map(str.lower, self.owns)) & set(map(str.lower, self.not_owns)))
        if overlap:
            defects.append(f"owns/not_owns: contradictory entries {overlap}")

        for relation in ("upstream", "downstream"):
            if not any(d.relation == relation for d in self.dependencies):
                defects.append(f"dependencies: no {relation} relationship declared")

        return defects

    @property
    def is_complete(self) -> bool:
        return not self.validate()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
