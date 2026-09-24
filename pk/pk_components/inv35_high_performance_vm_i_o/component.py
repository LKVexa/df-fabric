"""INV-35 - High-performance VM I/O.

High-performance VM I/O is virtio done properly: shared-memory rings, notification suppression and a vhost-style datapath that keeps the VMM out of the hot path. Every one of those tricks is also a way for a guest to corrupt the host, so descriptor validation here is not optional.

The component answers all 100 requirements of the INV-35 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Maximum descriptors in one chain before it is treated as malformed.
MAX_CHAIN = 16

#: Maximum in-flight descriptors per queue.
QUEUE_DEPTH = 64


class DescriptorInvalid(PermissionError):
    """Raised when a guest-posted descriptor cannot be trusted."""


class QueueFull(RuntimeError):
    """Raised when a queue is already at its in-flight bound."""


@dataclass(frozen=True)
class MemoryRegion:
    base: int
    length: int

    @property
    def limit(self) -> int:
        return self.base + self.length

    def contains(self, address: int, size: int) -> bool:
        return address >= self.base and address + size <= self.limit


@dataclass(frozen=True)
class Descriptor:
    index: int
    address: int
    length: int
    next_index: int | None = None


@dataclass
class VirtQueue:
    """One virtqueue with descriptor validation against the guest's own memory."""

    name: str
    regions: tuple                      # the guest's registered memory regions
    in_flight: int = 0
    pending: int = 0
    notifications_suppressed: int = 0
    completed: list = field(default_factory=list)

    def _in_guest_memory(self, address: int, size: int) -> bool:
        return any(r.contains(address, size) for r in self.regions)

    def submit(self, chain: dict, head: int) -> dict:
        """Walk a descriptor chain, validating every link before it is used."""
        if self.in_flight >= QUEUE_DEPTH:
            raise QueueFull(f"{self.name}: {QUEUE_DEPTH} descriptors already in flight")

        seen, index, length, walked = set(), head, 0, []
        while index is not None:
            if index in seen:
                raise DescriptorInvalid(f"{self.name}: descriptor chain loops at {index}")
            if len(walked) >= MAX_CHAIN:
                raise DescriptorInvalid(f"{self.name}: chain exceeds {MAX_CHAIN} descriptors")
            seen.add(index)
            desc = chain.get(index)
            if desc is None:
                raise DescriptorInvalid(f"{self.name}: descriptor {index} is not in the ring")
            if desc.length < 0:
                raise DescriptorInvalid(f"{self.name}: descriptor {index} has a negative length")
            if not self._in_guest_memory(desc.address, desc.length):
                raise DescriptorInvalid(
                    f"{self.name}: descriptor {index} at {hex(desc.address)}+{desc.length} "
                    "is outside guest memory")
            walked.append(index)
            length += desc.length
            index = desc.next_index

        self.in_flight += 1
        self.pending += 1
        return {"schema": "PK_VIRTQUEUE_SUBMIT/1", "queue": self.name,
                "descriptors": walked, "bytes": length, "validated": True}

    def complete(self, *, guest_wants_notification: bool) -> dict:
        """Complete one descriptor; suppression must never elide a needed wakeup."""
        if self.in_flight == 0:
            raise RuntimeError(f"{self.name}: nothing in flight to complete")
        self.in_flight -= 1
        self.pending -= 1
        # A wakeup may only be suppressed when the guest asked for suppression AND
        # nothing is left pending -- otherwise the guest would sleep on live work.
        suppress = guest_wants_notification is False and self.pending == 0
        if suppress:
            self.notifications_suppressed += 1
        self.completed.append({"notified": not suppress})
        return {"schema": "PK_VIRTQUEUE_COMPLETE/1", "queue": self.name,
                "notified": not suppress, "pending": self.pending}


class HighPerformanceVmIOComponent(Component):
    """Master-applied component for INV-35."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        regions = (MemoryRegion(0x10000, 0x10000),)
        q = VirtQueue("vq0", regions)
        chain = {0: Descriptor(0, 0x10000, 256, 1), 1: Descriptor(1, 0x10100, 256)}
        result = q.submit(chain, head=0)
        assert result["validated"] and result["bytes"] == 512 and result["descriptors"] == [0, 1]
        findings[5] = self.satisfied(
            items[5],
            f"A two-descriptor chain is walked and every link bounds-checked before use "
            f"({result['bytes']} bytes across {len(result['descriptors'])} descriptors).",
            *self._evidence("component.py::VirtQueue.submit"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        regions = (MemoryRegion(0x10000, 0x1000),)
        q = VirtQueue("vq0", regions)
        proven = []
        try:
            q.submit({0: Descriptor(0, 0x0, 64)}, head=0)
        except DescriptorInvalid:
            proven.append("host-memory pointer")
        try:
            q.submit({0: Descriptor(0, 0x10000, 64, 1), 1: Descriptor(1, 0x10040, 64, 0)}, head=0)
        except DescriptorInvalid:
            proven.append("chain loop")
        try:
            q.submit({0: Descriptor(0, 0x10000, -1)}, head=0)
        except DescriptorInvalid:
            proven.append("negative length")
        try:
            q.submit({0: Descriptor(0, 0x10000, 64, 9)}, head=0)
        except DescriptorInvalid:
            proven.append("dangling next index")
        assert len(proven) == 4, proven
        findings[6] = self.satisfied(
            items[6],
            f"Four hostile descriptor shapes are refused before dereference: {', '.join(proven)}. The guest "
            "controls the ring, so nothing on it is trusted without validation.",
            *self._evidence("component.py::VirtQueue.submit"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        regions = (MemoryRegion(0x10000, 0x100000),)
        q = VirtQueue("vq0", regions)
        chain = {0: Descriptor(0, 0x10000, 8)}
        for _ in range(QUEUE_DEPTH):
            q.submit(chain, head=0)
        try:
            q.submit(chain, head=0)
        except QueueFull:
            findings[5] = self.satisfied(
                items[5],
                f"In-flight work is bounded at {QUEUE_DEPTH} descriptors per queue, so a guest cannot "
                "flood the host by posting without limit.",
                *self._evidence("component.py::VirtQueue.submit"))
        # Two in flight: the first completion must notify even though suppression was requested.
        fresh = VirtQueue("vq1", regions)
        fresh.submit(chain, head=0)
        fresh.submit(chain, head=0)
        first = fresh.complete(guest_wants_notification=False)
        second = fresh.complete(guest_wants_notification=False)
        assert first["notified"] and not second["notified"]
        findings[8] = self.satisfied(
            items[8],
            "Notification suppression only applies once the queue is drained: with work still pending the "
            "wakeup is sent anyway, so a suppressed notification can never strand the guest.",
            *self._evidence("component.py::VirtQueue.complete"))
        return findings

COMPONENT = HighPerformanceVmIOComponent
