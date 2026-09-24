"""INV-20 - HTTP component worlds.

An HTTP component world is the smallest useful thing a serverless component can be: a world that imports an outgoing-request capability and exports an incoming-request handler, with both bodies as streams and trailers as completions. Because the world is explicit, a component that was never granted outgoing HTTP simply cannot make a call.

The component answers all 100 requirements of the INV-20 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class EgressDenied(PermissionError):
    """Raised when a component calls a host its world did not grant."""


class NoOutgoingCapability(PermissionError):
    """Raised when a world imports no outgoing HTTP at all."""


class BodyTooLarge(RuntimeError):
    """Raised when a streamed body exceeds the workload's limit."""


@dataclass
class BodyStream:
    """A request or response body, streamed in chunks and bounded in total size."""

    limit: int = 1 << 20
    chunks: list = field(default_factory=list)
    total: int = 0
    peak_buffered: int = 0

    def write(self, chunk: bytes) -> None:
        if self.total + len(chunk) > self.limit:
            raise BodyTooLarge(f"body would exceed {self.limit} bytes")
        self.total += len(chunk)
        self.chunks.append(chunk)
        self.peak_buffered = max(self.peak_buffered, len(self.chunks))

    def forward(self) -> bytes:
        """Hand one chunk onward; the buffer never holds the whole body."""
        return self.chunks.pop(0) if self.chunks else b""


@dataclass
class HttpWorld:
    """One component's HTTP world: what it exports, and what it may reach."""

    name: str
    handler: object = None
    #: Hosts this world grants outgoing HTTP to.  Empty means no egress at all.
    allowed_hosts: frozenset = frozenset()
    outgoing_granted: bool = False
    egress_denials: int = 0
    handled: int = 0

    def export_handler(self, fn) -> None:
        if self.handler is not None:
            raise ValueError(f"world {self.name} already exports a handler")
        self.handler = fn

    def handle(self, request):
        if self.handler is None:
            raise RuntimeError(f"world {self.name} exports no handler")
        self.handled += 1
        return self.handler(request)

    def fetch(self, host: str):
        if not self.outgoing_granted:
            raise NoOutgoingCapability(f"world {self.name} imports no outgoing HTTP")
        if host not in self.allowed_hosts:
            self.egress_denials += 1
            raise EgressDenied(f"{host} is not in world {self.name}'s allow-list")
        return ("ok", host)


class HttpComponentWorldsComponent(Component):
    """Master-applied component for INV-20."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        w = HttpWorld("api", allowed_hosts=frozenset({"upstream.internal"}), outgoing_granted=True)
        w.export_handler(lambda req: ("200", req))
        assert w.handle({"path": "/"}) == ("200", {"path": "/"})
        duplicated = False
        try:
            w.export_handler(lambda req: None)
        except ValueError:
            duplicated = True
        assert duplicated
        findings[0] = self.satisfied(
            items[0],
            "A world exports exactly one incoming-request handler; a second export is refused, so the "
            "entry point of a component is unambiguous at link time.",
            *self._evidence("component.py::HttpWorld.export_handler"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        granted = HttpWorld("api", allowed_hosts=frozenset({"upstream.internal"}), outgoing_granted=True)
        assert granted.fetch("upstream.internal") == ("ok", "upstream.internal")
        denied = False
        try:
            granted.fetch("169.254.169.254")
        except EgressDenied:
            denied = True

        sealed = HttpWorld("pure")
        no_cap = False
        try:
            sealed.fetch("upstream.internal")
        except NoOutgoingCapability:
            no_cap = True
        assert denied and no_cap and granted.egress_denials == 1
        findings[0] = self.satisfied(
            items[0],
            "Egress is a property of the world: an allow-listed host succeeds, the metadata address is "
            "denied, and a world that imports no outgoing HTTP cannot reach anything at all -- so a "
            "component's reachable surface is reviewable before it runs.",
            *self._evidence("component.py::HttpWorld.fetch"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        body = BodyStream(limit=1 << 20)
        forwarded = 0
        for _ in range(64):
            body.write(b"x" * 1024)
            forwarded += len(body.forward())
        assert body.peak_buffered == 1 and forwarded == 64 * 1024
        oversized = False
        small = BodyStream(limit=16)
        try:
            small.write(b"y" * 17)
        except BodyTooLarge:
            oversized = True
        assert oversized
        findings[0] = self.satisfied(
            items[0],
            f"A {forwarded}-byte body is forwarded a chunk at a time with at most "
            f"{body.peak_buffered} chunk held, and a body over the workload's limit is refused rather "
            "than buffered, so memory is bounded independently of body size.",
            *self._evidence("component.py::BodyStream"))
        return findings

COMPONENT = HttpComponentWorldsComponent
