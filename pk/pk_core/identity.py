"""Stable identifiers: element ids, the ten checklist dimensions, the ten workflow stages."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_ELEMENT_RE = re.compile(r"^(INV|PLN|SCH|GAP)-(\d{2})$")
_CHECK_RE = re.compile(r"^(INV|PLN|SCH|GAP)-(\d{2})-C(\d{3})$")


@dataclass(frozen=True, order=True)
class ElementId:
    """One of the 95 architectural elements, e.g. ``PLN-01``."""

    family: str
    number: int

    def __post_init__(self) -> None:
        if self.family not in ("INV", "PLN", "SCH", "GAP"):
            raise ValueError(f"unknown element family: {self.family!r}")
        if not 1 <= self.number <= 99:
            raise ValueError(f"element number out of range: {self.number}")

    @classmethod
    def parse(cls, text: str) -> "ElementId":
        m = _ELEMENT_RE.match(text.strip())
        if not m:
            raise ValueError(f"not an element id: {text!r}")
        return cls(m.group(1), int(m.group(2)))

    def check(self, ordinal: int) -> str:
        """Return the canonical checklist id for ``ordinal`` (1-100)."""
        if not 1 <= ordinal <= 100:
            raise ValueError(f"checklist ordinal out of range: {ordinal}")
        return f"{self}-C{ordinal:03d}"

    @staticmethod
    def split_check(check_id: str) -> tuple["ElementId", int]:
        m = _CHECK_RE.match(check_id.strip())
        if not m:
            raise ValueError(f"not a checklist id: {check_id!r}")
        return ElementId(m.group(1), int(m.group(2))), int(m.group(3))

    def __str__(self) -> str:
        return f"{self.family}-{self.number:02d}"


class Dimension(str, Enum):
    """The ten checklist dimensions; each owns exactly ten requirements."""

    ARCHITECTURE = "Architecture & Scope"
    REQUIREMENTS = "Requirements & Semantics"
    INTERFACES = "Interfaces & Integration"
    IMPLEMENTATION = "Implementation & Configuration"
    SECURITY = "Security, Trust & Isolation"
    RESILIENCE = "Resilience & Failure Handling"
    PERFORMANCE = "Performance & Resource Efficiency"
    OBSERVABILITY = "Observability & Explainability"
    TESTING = "Testing & Certification"
    OPERATIONS = "Operations, Release & Governance"

    @property
    def ordinal(self) -> int:
        return DIMENSIONS.index(self)

    @property
    def span(self) -> range:
        """The 1-based checklist ordinals this dimension covers."""
        base = self.ordinal * 10
        return range(base + 1, base + 11)

    @classmethod
    def for_ordinal(cls, ordinal: int) -> "Dimension":
        if not 1 <= ordinal <= 100:
            raise ValueError(f"checklist ordinal out of range: {ordinal}")
        return DIMENSIONS[(ordinal - 1) // 10]

    @property
    def slug(self) -> str:
        return self.name.lower()


DIMENSIONS: tuple[Dimension, ...] = tuple(Dimension)


class Stage(str, Enum):
    """The ten workflow stages W0-W9 applied to every checklist item."""

    W0 = "Intake & Context Lock"
    W1 = "Baseline & Gap Analysis"
    W2 = "Design & Acceptance Definition"
    W3 = "Implementation"
    W4 = "Integration"
    W5 = "Security & Hardening"
    W6 = "Resilience & Performance"
    W7 = "Verification & Certification"
    W8 = "Release & Rollback"
    W9 = "Evidence Closeout"

    @property
    def ordinal(self) -> int:
        return int(self.name[1:])

    @property
    def title(self) -> str:
        return f"{self.name} {self.value}"


STAGES: tuple[Stage, ...] = tuple(Stage)
