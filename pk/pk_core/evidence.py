"""Append-only, hash-chained evidence ledger.

W9 (Evidence Closeout) is only meaningful if the record cannot be quietly
rewritten, so each record carries the digest of its predecessor.  The chain is
verifiable offline with :meth:`EvidenceLedger.verify`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    """One sealed entry in the ledger."""

    sequence: int
    element: str
    stage: str
    summary: str
    payload: dict
    recorded_at: str
    previous: str
    self_digest: str = field(default="")

    def compute_digest(self) -> str:
        return digest(
            {
                "sequence": self.sequence,
                "element": self.element,
                "stage": self.stage,
                "summary": self.summary,
                "payload": self.payload,
                "recorded_at": self.recorded_at,
                "previous": self.previous,
            }
        )

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "element": self.element,
            "stage": self.stage,
            "summary": self.summary,
            "payload": self.payload,
            "recorded_at": self.recorded_at,
            "previous": self.previous,
            "digest": self.self_digest,
        }


class EvidenceLedger:
    """Append-only ledger of workflow evidence for one or more elements."""

    def __init__(self, path: str | Path | None = None, *, clock=None) -> None:
        self.path = Path(path) if path is not None else None
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: list[EvidenceRecord] = []
        if self.path is not None and self.path.exists():
            self._load()

    # -- writing ------------------------------------------------------
    def append(self, *, element: str, stage: str, summary: str, payload: dict) -> EvidenceRecord:
        previous = self._records[-1].self_digest if self._records else GENESIS
        record = EvidenceRecord(
            sequence=len(self._records),
            element=element,
            stage=stage,
            summary=summary,
            payload=payload,
            recorded_at=self._clock().isoformat(),
            previous=previous,
        )
        record = EvidenceRecord(**{**record.__dict__, "self_digest": record.compute_digest()})
        self._records.append(record)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        return record

    # -- reading ------------------------------------------------------
    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            self._records.append(
                EvidenceRecord(
                    sequence=row["sequence"],
                    element=row["element"],
                    stage=row["stage"],
                    summary=row["summary"],
                    payload=row["payload"],
                    recorded_at=row["recorded_at"],
                    previous=row["previous"],
                    self_digest=row["digest"],
                )
            )

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    @property
    def head(self) -> str:
        return self._records[-1].self_digest if self._records else GENESIS

    def for_element(self, element: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.element == element]

    # -- integrity ----------------------------------------------------
    def verify(self) -> list[str]:
        """Return a list of chain defects; empty means the ledger is intact."""
        defects: list[str] = []
        previous = GENESIS
        for index, record in enumerate(self._records):
            if record.sequence != index:
                defects.append(f"record {index}: sequence is {record.sequence}")
            if record.previous != previous:
                defects.append(f"record {index}: previous digest does not chain")
            if record.self_digest != record.compute_digest():
                defects.append(f"record {index}: payload does not match its digest")
            previous = record.self_digest
        return defects
