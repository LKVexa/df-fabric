"""GAP-04 - Disconnected-operation controller.

The disconnected-operation controller is what lets an edge site keep working when the control plane is gone. It grants a bounded autonomy lease, narrows what the site may decide for itself as the partition lengthens, and reconciles honestly on reconnect instead of pretending nothing happened.

The component answers all 100 requirements of the GAP-04 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Degradation tiers, widest authority first. The site narrows as the partition lengthens.
TIERS = ("full", "sustain", "freeze", "expired")

#: What each tier permits the site to decide for itself.
PERMITTED = {
    "full":    {"restart", "rebalance", "admit-known", "admit-new", "scale"},
    "sustain": {"restart", "rebalance", "admit-known"},
    "freeze":  {"restart"},
    "expired": set(),
}

#: Partition age at which each tier takes over.
TIER_AT = ((0, "full"), (30, "sustain"), (120, "freeze"))


class LeaseExpired(PermissionError):
    """Raised when a decision is attempted with no valid autonomy lease."""


class NotPermittedAtTier(PermissionError):
    """Raised when a decision is above the site's current degradation tier."""


@dataclass
class AutonomyController:
    """Bounded local authority for one site during a control-plane partition."""

    site: str
    granted_at: int = 0
    lease_ticks: int = 180
    partitioned_since: int | None = None
    decisions: list = field(default_factory=list)
    policy_cached_at: int = 0

    # -- lease -------------------------------------------------------
    def expires_at(self) -> int:
        return self.granted_at + self.lease_ticks

    def renew(self, now: int, *, control_plane_reachable: bool) -> int:
        """A lease may only be renewed with real control-plane contact."""
        if not control_plane_reachable:
            raise LeaseExpired(f"{self.site}: cannot renew a lease without control-plane contact")
        self.granted_at = now
        self.partitioned_since = None
        return self.expires_at()

    def partition(self, now: int) -> None:
        if self.partitioned_since is None:
            self.partitioned_since = now

    def tier(self, now: int) -> str:
        if now >= self.expires_at():
            return "expired"
        if self.partitioned_since is None:
            return "full"
        age = now - self.partitioned_since
        current = "full"
        for at, name in TIER_AT:
            if age >= at:
                current = name
        return current

    # -- decisions ---------------------------------------------------
    def decide(self, kind: str, subject: str, now: int) -> dict:
        """Take a local decision, or refuse it. Every taken decision is recorded."""
        tier = self.tier(now)
        if tier == "expired":
            raise LeaseExpired(f"{self.site}: autonomy lease expired at {self.expires_at()}")
        if kind not in PERMITTED[tier]:
            raise NotPermittedAtTier(f"{self.site}: {kind!r} is not permitted at tier {tier!r}")
        record = {"kind": kind, "subject": subject, "at": now, "tier": tier,
                  "policy_age": now - self.policy_cached_at}
        self.decisions.append(record)
        return record

    def reconcile(self, now: int) -> dict:
        """On reconnect, hand back every local decision -- including the awkward ones."""
        record = {"schema": "PK_RECONCILIATION_RECORD/1", "site": self.site,
                  "partitioned_since": self.partitioned_since,
                  "reconnected_at": now,
                  "decisions": list(self.decisions),
                  "decision_count": len(self.decisions),
                  "max_policy_age": max((d["policy_age"] for d in self.decisions), default=0)}
        self.decisions = []
        self.partitioned_since = None
        return record


class DisconnectedOperationControllerComponent(Component):
    """Master-applied component for GAP-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=300)
        c.partition(0)
        assert c.tier(0) == "full"
        assert c.tier(40) == "sustain"
        assert c.tier(130) == "freeze"
        c.decide("admit-new", "w1", 0)
        c.decide("admit-known", "w2", 40)
        c.decide("restart", "w3", 130)
        record = c.reconcile(140)
        assert record["decision_count"] == 3 and not c.decisions
        findings[5] = self.satisfied(
            items[5],
            f"Degradation is monotone with partition age (full -> sustain -> freeze) and all "
            f"{record['decision_count']} local decisions survive into the reconciliation record.",
            *self._evidence("component.py::AutonomyController"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=60)
        c.partition(0)
        try:
            c.renew(30, control_plane_reachable=False)
        except LeaseExpired:
            findings[3] = self.satisfied(
                items[3],
                "A lease cannot be renewed without real control-plane contact, so a site cannot extend its "
                "own authority by staying partitioned.",
                *self._evidence("component.py::AutonomyController.renew"))
        try:
            c.decide("admit-new", "w", 61)
        except LeaseExpired:
            findings[1] = self.satisfied(
                items[1],
                "Once the lease expires the site decides nothing at all; authority goes to zero rather than "
                "defaulting open.",
                *self._evidence("component.py::AutonomyController.decide"))
        fresh = AutonomyController("ams", granted_at=0, lease_ticks=300)
        fresh.partition(0)
        try:
            fresh.decide("admit-new", "w", 130)
        except NotPermittedAtTier:
            findings[5] = self.satisfied(
                items[5],
                "Admitting new work is refused at the freeze tier, so a long partition narrows what the "
                "site may do instead of widening it.",
                *self._evidence("component.py::PERMITTED"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=300, policy_cached_at=0)
        c.partition(0)
        c.decide("restart", "w", 100)
        record = c.reconcile(110)
        assert record["max_policy_age"] == 100
        findings[7] = self.satisfied(
            items[7],
            "Each offline decision carries the age of the policy it was taken under, so a decision made on "
            "stale policy is explainable after the fact rather than indistinguishable.",
            *self._evidence("component.py::AutonomyController.decide"))
        return findings

COMPONENT = DisconnectedOperationControllerComponent
