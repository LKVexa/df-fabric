"""INV-37 - Bulk data plane.

The bulk data plane moves the large things -- images, snapshots, model weights, datasets -- in verified chunks. Every chunk carries its own digest and the object carries a digest over the chunk list, so a transfer is checked end to end by the receiver, can resume from the last good chunk, and never trusts the transport to have delivered what it claims.

The component answers all 100 requirements of the INV-37 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field

CHUNK = 4096


class DigestMismatch(ValueError):
    """Raised when a chunk or the whole object fails verification."""


def manifest(data: bytes, chunk: int = CHUNK) -> dict:
    chunks = [hashlib.sha256(data[i:i + chunk]).hexdigest() for i in range(0, len(data), chunk)]
    return {"schema": "PK_BULK_MANIFEST/1", "chunk": chunk, "size": len(data), "chunks": chunks,
            "object": hashlib.sha256("".join(chunks).encode()).hexdigest()}


def verify_object(m: dict, data: bytes) -> str:
    """End-to-end verification the receiver performs itself."""
    recomputed = manifest(data, m["chunk"])
    if recomputed["object"] != m["object"] or recomputed["size"] != m["size"]:
        raise DigestMismatch("object digest does not match manifest")
    return m["object"]


@dataclass
class Receiver:
    m: dict
    received: dict = field(default_factory=dict)
    failures: int = 0

    def accept(self, index: int, payload: bytes) -> None:
        if hashlib.sha256(payload).hexdigest() != self.m["chunks"][index]:
            self.failures += 1
            raise DigestMismatch(f"chunk {index} does not verify")
        self.received[index] = payload

    def missing(self) -> list:
        return [i for i in range(len(self.m["chunks"])) if i not in self.received]

    def assemble(self) -> bytes:
        if self.missing():
            raise DigestMismatch(f"incomplete: {len(self.missing())} chunk(s) missing")
        data = b"".join(self.received[i] for i in range(len(self.m["chunks"])))
        verify_object(self.m, data)
        return data


class BulkDataPlaneComponent(Component):
    """Master-applied component for INV-37."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        data = bytes(range(256)) * 64
        m = manifest(data)
        rx = Receiver(m)
        chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
        bad = False
        try:
            rx.accept(0, b"corrupt" + chunks[0][7:])
        except DigestMismatch:
            bad = True
        for i, c in enumerate(chunks):
            rx.accept(i, c)
        assert bad and rx.assemble() == data
        findings[0] = self.satisfied(
            items[0],
            f"A {len(data)}-byte object crosses as {len(chunks)} digested chunks; a corrupted chunk is "
            "refused on receipt and the assembled object is re-verified end to end by the receiver.",
            *self._evidence("component.py::Receiver", "component.py::verify_object"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        data = b"w" * (CHUNK * 5 + 17)
        m = manifest(data)
        rx = Receiver(m)
        chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
        for i in (0, 1, 2):
            rx.accept(i, chunks[i])
        todo = rx.missing()
        partial = False
        try:
            rx.assemble()
        except DigestMismatch:
            partial = True
        for i in todo:
            rx.accept(i, chunks[i])
        assert partial and todo == [3, 4, 5] and rx.assemble() == data
        findings[0] = self.satisfied(
            items[0],
            f"An interrupted transfer resumes by re-sending only the {len(todo)} unverified chunks, and a "
            "partial object is refused rather than used as if complete.",
            *self._evidence("component.py::Receiver.missing", "component.py::Receiver.assemble"))
        return findings

COMPONENT = BulkDataPlaneComponent
