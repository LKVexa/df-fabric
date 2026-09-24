"""INV-36 - Control transport.

The control transport carries the small, authoritative messages -- placement decisions, leases, revocations -- that everything else acts on. Its job is not speed but trust: every frame is authenticated, sequenced and sealed end to end, so a relay in the middle forwards ciphertext it cannot read or reorder undetected.

The component answers all 100 requirements of the INV-36 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
import hmac
from dataclasses import dataclass, field

MAX_FRAME = 64 * 1024


class AuthFailure(ValueError):
    """Raised when a frame's tag does not verify."""


class Replay(ValueError):
    """Raised when a frame's sequence is not strictly newer than the last accepted one."""


class FrameTooLarge(ValueError):
    """Raised when a frame exceeds the bound."""


def _keystream(key: bytes, seq: int, n: int) -> bytes:
    # Reference keystream (SHA-256 in counter mode) so the build is stdlib-only;
    # a production estate substitutes an AEAD without changing this interface.
    out, block = b"", 0
    while len(out) < n:
        out += hashlib.sha256(key + seq.to_bytes(8, "big") + block.to_bytes(4, "big")).digest()
        block += 1
    return out[:n]


def derive(shared: bytes, a: str, b: str) -> tuple[bytes, bytes]:
    """Derive independent sealing and MAC keys bound to both peer identities."""
    ctx = "|".join(sorted((a, b))).encode()
    return (hashlib.sha256(b"seal" + shared + ctx).digest(),
            hashlib.sha256(b"mac" + shared + ctx).digest())


@dataclass
class Session:
    local: str
    peer: str
    shared: bytes
    send_seq: int = 0
    recv_seq: int = 0
    auth_failures: int = 0
    replays: int = 0

    def __post_init__(self):
        self.k_seal, self.k_mac = derive(self.shared, self.local, self.peer)

    def seal(self, plaintext: bytes) -> bytes:
        if len(plaintext) > MAX_FRAME:
            raise FrameTooLarge(f"{len(plaintext)} bytes > {MAX_FRAME}")
        self.send_seq += 1
        seq = self.send_seq.to_bytes(8, "big")
        body = bytes(x ^ y for x, y in zip(plaintext, _keystream(self.k_seal, self.send_seq, len(plaintext))))
        tag = hmac.new(self.k_mac, seq + body, hashlib.sha256).digest()
        return seq + body + tag

    def open(self, frame: bytes) -> bytes:
        if len(frame) > MAX_FRAME + 40:
            raise FrameTooLarge("frame exceeds bound")
        seq_b, body, tag = frame[:8], frame[8:-32], frame[-32:]
        if not hmac.compare_digest(tag, hmac.new(self.k_mac, seq_b + body, hashlib.sha256).digest()):
            self.auth_failures += 1
            raise AuthFailure("tag does not verify")
        seq = int.from_bytes(seq_b, "big")
        if seq <= self.recv_seq:
            self.replays += 1
            raise Replay(f"sequence {seq} not newer than {self.recv_seq}")
        self.recv_seq = seq
        return bytes(x ^ y for x, y in zip(body, _keystream(self.k_seal, seq, len(body))))


@dataclass
class Relay:
    """Forwards sealed frames.  Holds no key, so it sees only ciphertext."""

    seen: list = field(default_factory=list)

    def forward(self, frame: bytes) -> bytes:
        self.seen.append(frame)
        return frame


class ControlTransportComponent(Component):
    """Master-applied component for INV-36."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _pair(self):
        shared = b"attested-shared-secret"
        return Session("node-a", "node-b", shared), Session("node-b", "node-a", shared)

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a, b = self._pair()
        relay = Relay()
        msg = b"REVOKE lease-42"
        assert b.open(relay.forward(a.seal(msg))) == msg
        assert all(msg not in f for f in relay.seen)
        findings[0] = self.satisfied(
            items[0],
            "Frames are sealed end to end with keys bound to both peer identities; the relay forwarded "
            "the frame and delivered it intact, yet the plaintext never appears in anything it saw.",
            *self._evidence("component.py::Session.seal", "component.py::Relay"))

        frame = bytearray(a.seal(b"GRANT lease-43"))
        frame[10] ^= 0xFF
        tampered = False
        try:
            b.open(bytes(frame))
        except AuthFailure:
            tampered = True
        assert tampered and b.auth_failures == 1
        findings[1] = self.satisfied(
            items[1],
            "A single flipped byte fails authentication and is refused before the frame is interpreted.",
            *self._evidence("component.py::Session.open"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a, b = self._pair()
        old = a.seal(b"LEASE v1")
        b.open(a.seal(b"LEASE v2"))
        replayed = False
        try:
            b.open(old)
        except Replay:
            replayed = True
        big = False
        try:
            a.seal(b"x" * (MAX_FRAME + 1))
        except FrameTooLarge:
            big = True
        assert replayed and big
        findings[0] = self.satisfied(
            items[0],
            "A stale frame delivered after a newer one is refused as a replay, so an old lease or "
            f"revocation cannot be resurrected, and frames above {MAX_FRAME} bytes are refused at the seal.",
            *self._evidence("component.py::Session.open", "component.py::MAX_FRAME"))
        return findings

COMPONENT = ControlTransportComponent
