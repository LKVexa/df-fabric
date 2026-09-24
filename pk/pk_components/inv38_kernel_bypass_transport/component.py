"""INV-38 - Kernel-bypass transport.

Kernel-bypass transport hands network or storage queues straight to user space, skipping the kernel copy. The speed comes from the application touching device-visible memory directly, which is exactly the danger: every access must fall inside a registered region, and the sealed end-to-end channel above it must not be weakened just because the path got faster.

The component answers all 100 requirements of the INV-38 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class OutOfBounds(ValueError):
    """Raised when a descriptor reaches outside its registered region."""


class NotRegistered(KeyError):
    """Raised for a region key that is unknown or was deregistered."""


class RingFull(RuntimeError):
    """Raised when the submission ring has no free slots."""


@dataclass
class BypassQueue:
    ring_size: int = 8
    available: bool = True
    regions: dict = field(default_factory=dict)
    ring: list = field(default_factory=list)
    completions: list = field(default_factory=list)
    _next_key: int = 1
    violations: int = 0
    fallbacks: int = 0

    def register(self, base: int, length: int) -> int:
        key = self._next_key
        self._next_key += 1
        self.regions[key] = (base, length)
        return key

    def deregister(self, key: int) -> None:
        self.regions.pop(key, None)

    def post(self, key: int, addr: int, length: int, payload: bytes) -> str:
        if not self.available:
            self.fallbacks += 1
            self.completions.append(("kernel", payload))
            return "kernel"
        if key not in self.regions:
            raise NotRegistered(key)
        base, size = self.regions[key]
        if addr < base or addr + length > base + size:
            self.violations += 1
            raise OutOfBounds(f"{addr:#x}+{length} outside region {key}")
        if len(self.ring) >= self.ring_size:
            raise RingFull(f"{self.ring_size} slots in use")
        self.ring.append(payload)
        return "bypass"

    def poll(self) -> int:
        n = len(self.ring)
        self.completions.extend(("bypass", p) for p in self.ring)
        self.ring.clear()
        return n


class KernelBypassTransportComponent(Component):
    """Master-applied component for INV-38."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        q = BypassQueue()
        key = q.register(0x1000, 0x1000)
        assert q.post(key, 0x1000, 512, b"ok") == "bypass"
        escaped = False
        try:
            q.post(key, 0x1F00, 512, b"x")
        except OutOfBounds:
            escaped = True
        q.deregister(key)
        stale = False
        try:
            q.post(key, 0x1000, 16, b"x")
        except NotRegistered:
            stale = True
        assert escaped and stale
        findings[0] = self.satisfied(
            items[0],
            "Every descriptor is bounds-checked against its registered region: one crossing the region's "
            "end is refused, and a key reused after deregistration is unknown to the device.",
            *self._evidence("component.py::BypassQueue.post"))

        inv36 = sibling("INV-36")
        if inv36 is not None:
            a = inv36.Session("a", "b", b"s")
            b = inv36.Session("b", "a", b"s")
            q2 = BypassQueue()
            k2 = q2.register(0, 1 << 16)
            frame = a.seal(b"secret")
            q2.post(k2, 0, len(frame), frame)
            q2.poll()
            carried = q2.completions[0][1]
            assert b"secret" not in carried and b.open(carried) == b"secret"
            findings[1] = self.satisfied(
                items[1],
                "The fast path carries INV-36 sealed frames without unsealing them: the bytes on the "
                "ring contain no plaintext and still open at the peer, so speed does not cost sealing.",
                *self._evidence("component.py::BypassQueue"), "INV-36/Session")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        q = BypassQueue(ring_size=2)
        k = q.register(0, 4096)
        q.post(k, 0, 8, b"1")
        q.post(k, 8, 8, b"2")
        full = False
        try:
            q.post(k, 16, 8, b"3")
        except RingFull:
            full = True
        drained = q.poll()
        down = BypassQueue(available=False)
        assert full and drained == 2 and down.post(0, 0, 1, b"z") == "kernel" and down.fallbacks == 1
        findings[0] = self.satisfied(
            items[0],
            "A full ring refuses instead of dropping a completion, draining restores capacity, and when "
            "bypass is unavailable the same post falls back to the kernel path transparently.",
            *self._evidence("component.py::BypassQueue.post", "component.py::BypassQueue.poll"))
        return findings

COMPONENT = KernelBypassTransportComponent
