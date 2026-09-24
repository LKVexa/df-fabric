"""GAP-12 - WAN resilience and NAT traversal.

WAN resilience and NAT traversal is the plumbing that keeps an edge site reachable from behind a carrier-grade NAT on a flaky link. It escalates through connection strategies in cost order, backs off honestly, and reports the link as down rather than pretending a stale path still works.

The component answers all 100 requirements of the GAP-12 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Connection strategies in ascending cost order. Relay is always last.
STRATEGIES = ("direct", "hole-punch", "relay")

#: Backoff: base interval, multiplier, and the ceiling it may never exceed.
BACKOFF_BASE, BACKOFF_FACTOR, BACKOFF_CEILING = 1, 2, 60

#: A successful probe older than this no longer counts as evidence of health.
PROBE_FRESHNESS = 30


class Partitioned(RuntimeError):
    """Raised when every connection strategy has been exhausted for a peer."""


@dataclass
class Path:
    """Path state for one site pair, escalated in cost order."""

    peer: str
    strategy: str | None = None
    last_success: int | None = None
    attempts: list = field(default_factory=list)
    failures: int = 0

    def backoff(self) -> int:
        """Bounded exponential backoff; never exceeds the ceiling."""
        return min(BACKOFF_BASE * (BACKOFF_FACTOR ** self.failures), BACKOFF_CEILING)

    def healthy_at(self, now: int) -> bool:
        """Health requires a recent successful probe -- never an absence of failures."""
        return self.last_success is not None and now - self.last_success <= PROBE_FRESHNESS

    def connect(self, prober, now: int) -> dict:
        """Escalate through strategies in cost order until one probe succeeds."""
        for strategy in STRATEGIES:
            self.attempts.append({"strategy": strategy, "at": now})
            if prober(strategy):
                self.strategy = strategy
                self.last_success = now
                self.failures = 0
                return {"schema": "PK_PATH_STATE/1", "peer": self.peer, "strategy": strategy,
                        "healthy": True, "tried": [a["strategy"] for a in self.attempts[-STRATEGIES.index(strategy)-1:]]}
        self.failures += 1
        self.strategy = None
        raise Partitioned(
            f"{self.peer}: all strategies exhausted ({', '.join(STRATEGIES)}); "
            f"next retry in {self.backoff()}")

    def state(self, now: int) -> dict:
        return {"schema": "PK_PATH_STATE/1", "peer": self.peer, "strategy": self.strategy,
                "healthy": self.healthy_at(now),
                "last_success": self.last_success,
                "backoff": self.backoff(),
                "partitioned": not self.healthy_at(now)}


class WanResilienceAndNatTraversalComponent(Component):
    """Master-applied component for GAP-12."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        p = Path("ams")
        result = p.connect(lambda s: s == "direct", now=0)
        assert result["strategy"] == "direct" and [a["strategy"] for a in p.attempts] == ["direct"]

        q = Path("dub")
        q.connect(lambda s: s == "relay", now=0)
        assert [a["strategy"] for a in q.attempts] == list(STRATEGIES), \
            "relay was reached without trying cheaper strategies"
        findings[5] = self.satisfied(
            items[5],
            "Escalation is strictly cost-ordered: a direct path stops after one attempt, and relay is only "
            f"reached after {', '.join(STRATEGIES[:-1])} both fail.",
            *self._evidence("component.py::Path.connect"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = Path("ams")
        p.connect(lambda s: s == "direct", now=0)
        assert p.healthy_at(PROBE_FRESHNESS)
        assert not p.healthy_at(PROBE_FRESHNESS + 1), "stale path still reported healthy"
        findings[7] = self.satisfied(
            items[7],
            f"Health expires {PROBE_FRESHNESS} ticks after the last successful probe, so a path cannot be "
            "presented as working on the strength of an old success.",
            *self._evidence("component.py::Path.healthy_at"))
        q = Path("dub")
        q.connect(lambda s: s == "relay", now=0)
        inv36 = sibling("INV-36")
        if inv36 is None:
            findings[9] = self.partial(
                items[9],
                "Relay fallback is correctly last-resort but the relay itself is untrusted transit.",
                note="INV-36 Control transport is not installed here")
        else:
            a = inv36.Session("site-a", "site-b", b"attested")
            b = inv36.Session("site-b", "site-a", b"attested")
            relay = inv36.Relay()
            msg = b"LEASE renew node-7"
            assert b.open(relay.forward(a.seal(msg))) == msg
            assert all(msg not in f for f in relay.seen)
            forged = bytearray(relay.seen[0])
            forged[9] ^= 1
            try:
                b.open(bytes(forged))
                tamper_caught = False
            except inv36.AuthFailure:
                tamper_caught = True
            assert tamper_caught
            findings[9] = self.satisfied(
                items[9],
                "Relayed traffic is sealed end to end by INV-36: the relay forwarded the frame and it "
                "opened at the far site, the relay's view never contained the plaintext, and a byte "
                "altered in transit failed authentication -- the relay is transit, not a trusted party.",
                *self._evidence("contract.py"), "INV-36/Session", "INV-36/Relay")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Path("ams")
        for _ in range(12):
            try:
                p.connect(lambda s: False, now=0)
            except Partitioned:
                pass
        assert p.backoff() == BACKOFF_CEILING, f"backoff escaped its ceiling: {p.backoff()}"
        findings[4] = self.satisfied(
            items[4],
            f"Backoff grows exponentially but is clamped at {BACKOFF_CEILING}; twelve consecutive failures "
            "cannot turn retries into a self-inflicted denial-of-service.",
            *self._evidence("component.py::Path.backoff"))
        state = p.state(now=100)
        assert state["partitioned"] and not state["healthy"]
        findings[0] = self.satisfied(
            items[0],
            "With every strategy exhausted the path reports partitioned, giving GAP-04 the honest signal it "
            "needs instead of a masked failure.",
            *self._evidence("component.py::Path.state"))
        return findings

COMPONENT = WanResilienceAndNatTraversalComponent
