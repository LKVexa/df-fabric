"""The 100-requirement checklist each element must answer, and the findings against it."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from pk_core.identity import Dimension, ElementId, Stage


class Status(str, Enum):
    """Outcome of a checklist requirement after the workflow has run."""

    SATISFIED = "satisfied"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"

    @property
    def passing(self) -> bool:
        return self in (Status.SATISFIED, Status.NOT_APPLICABLE)


@dataclass(frozen=True)
class ChecklistItem:
    """One of the 100 requirements belonging to an element."""

    check_id: str
    ordinal: int
    dimension: Dimension
    requirement: str


@dataclass
class Finding:
    """A component's answer to one checklist requirement."""

    check_id: str
    status: Status
    stage: Stage
    statement: str
    artifacts: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["stage"] = self.stage.name
        return d


class Checklist:
    """The ordered 100 requirements for one element."""

    def __init__(self, element: ElementId, name: str, items: list[ChecklistItem]) -> None:
        if len(items) != 100:
            raise ValueError(f"{element}: expected 100 checklist items, got {len(items)}")
        self.element = element
        self.name = name
        self.items = sorted(items, key=lambda i: i.ordinal)
        self._by_id = {i.check_id: i for i in self.items}
        for ordinal, item in enumerate(self.items, start=1):
            if item.ordinal != ordinal:
                raise ValueError(f"{element}: checklist ordinals are not contiguous at {item.check_id}")
            if item.dimension is not Dimension.for_ordinal(ordinal):
                raise ValueError(f"{item.check_id}: dimension does not match its ordinal band")

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, check_id: str) -> ChecklistItem:
        return self._by_id[check_id]

    def ids(self) -> list[str]:
        return [i.check_id for i in self.items]

    def for_dimension(self, dimension: Dimension) -> list[ChecklistItem]:
        return [i for i in self.items if i.dimension is dimension]

    # -- persistence --------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "Checklist":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        element = ElementId.parse(data["element"])
        items = [
            ChecklistItem(
                check_id=row["check_id"],
                ordinal=row["ordinal"],
                dimension=Dimension(row["dimension"]),
                requirement=row["requirement"],
            )
            for row in data["items"]
        ]
        return cls(element, data.get("name", str(element)), items)

    def to_dict(self) -> dict:
        return {
            "element": str(self.element),
            "name": self.name,
            "item_count": len(self.items),
            "items": [
                {
                    "check_id": i.check_id,
                    "ordinal": i.ordinal,
                    "dimension": i.dimension.value,
                    "requirement": i.requirement,
                }
                for i in self.items
            ],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
