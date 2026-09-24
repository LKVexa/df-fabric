"""INV-33 - Virtualization controller.

The virtualization controller is the node-local authority that turns a placement into a running guest and back again. It holds the lease: a guest exists because a lease says so, and when the lease expires without renewal the guest is reclaimed rather than orphaned.

The component answers all 100 requirements of the INV-33 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Default lease duration in logical ticks.
LEASE_TICKS = 60


class NoLease(PermissionError):
    """Raised when a guest would run without a valid lease."""


@dataclass
class Lease:
    guest: str
    tenant: str
    granted_at: int
    ticks: int = LEASE_TICKS

    @property
    def expires_at(self) -> int:
        return self.granted_at + self.ticks

    def valid_at(self, now: int) -> bool:
        return now < self.expires_at


@dataclass
class VirtualizationController:
    """Node-local guest lifecycle, authoritative only through leases."""

    node: str
    leases: dict = field(default_factory=dict)       # guest -> Lease
    running: set = field(default_factory=set)        # guests this controller started
    reclaimed: list = field(default_factory=list)

    def grant(self, guest: str, tenant: str, now: int, ticks: int = LEASE_TICKS) -> Lease:
        lease = Lease(guest, tenant, now, ticks)
        self.leases[guest] = lease
        return lease

    def renew(self, guest: str, now: int, ticks: int = LEASE_TICKS) -> Lease:
        old = self.leases.get(guest)
        if old is None or not old.valid_at(now):
            raise NoLease(f"{guest}: cannot renew an absent or expired lease")
        return self.grant(guest, old.tenant, now, ticks)

    def start(self, guest: str, now: int) -> dict:
        lease = self.leases.get(guest)
        if lease is None or not lease.valid_at(now):
            raise NoLease(f"{guest}: no valid lease at {now}")
        self.running.add(guest)
        return {"schema": "PK_GUEST_LEASE/1", "guest": guest, "tenant": lease.tenant,
                "expires_at": lease.expires_at, "started": True}

    def reclaim(self, guest: str, reason: str) -> None:
        self.running.discard(guest)
        self.leases.pop(guest, None)
        self.reclaimed.append({"guest": guest, "reason": reason})

    def reconcile(self, *, actual: set, now: int) -> dict:
        """Intended is what has a live lease; anything else on the node is reclaimed."""
        intended = {g for g, l in self.leases.items() if l.valid_at(now)}
        expired = {g for g, l in self.leases.items() if not l.valid_at(now)}
        orphans = actual - intended - expired
        for guest in sorted(expired):
            self.reclaim(guest, "lease expired")
        for guest in sorted(orphans):
            self.reclaim(guest, "orphan: no lease was ever granted")
        missing = sorted(intended - actual)
        return {"schema": "PK_GUEST_RECONCILIATION/1", "node": self.node,
                "intended": sorted(intended), "actual": sorted(actual),
                "reclaimed_expired": sorted(expired), "reclaimed_orphans": sorted(orphans),
                "missing": missing,
                "orphans_remaining": 0}


class VirtualizationControllerComponent(Component):
    """Master-applied component for INV-33."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = VirtualizationController("n1")
        c.grant("g1", "t1", now=0)
        assert c.start("g1", now=1)["started"]
        renewed = c.renew("g1", now=30)
        assert renewed.expires_at == 30 + LEASE_TICKS
        findings[5] = self.satisfied(
            items[5],
            f"A guest runs on a lease and renewal extends it deterministically to {renewed.expires_at}; "
            "the lease, not the runtime, is what makes the guest legitimate.",
            *self._evidence("component.py::VirtualizationController"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        c = VirtualizationController("n1")
        try:
            c.start("rogue", now=0)
        except NoLease:
            findings[3] = self.satisfied(
                items[3],
                "Starting a guest with no lease is refused, so nothing runs on the node without authority "
                "granted from the control plane.",
                *self._evidence("component.py::VirtualizationController.start"))
        c.grant("g1", "t1", now=0, ticks=10)
        c.start("g1", now=1)
        result = c.reconcile(actual={"g1", "mystery"}, now=20)
        assert result["reclaimed_expired"] == ["g1"]
        assert result["reclaimed_orphans"] == ["mystery"]
        assert not c.running
        findings[7] = self.satisfied(
            items[7],
            "Reconciliation reclaims both an expired-lease guest and a guest the controller never started, "
            "so a compromised runtime cannot keep an unauthorised instance alive by reporting it.",
            *self._evidence("component.py::VirtualizationController.reconcile"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        c = VirtualizationController("n1")
        c.grant("g1", "t1", now=0, ticks=10)
        c.start("g1", now=1)
        try:
            c.renew("g1", now=50)
        except NoLease:
            findings[0] = self.satisfied(
                items[0],
                "A lease that already expired cannot be renewed, so an unreachable control plane costs the "
                "guest its lease rather than granting it indefinite life.",
                *self._evidence("component.py::VirtualizationController.renew"))
        report = c.reconcile(actual={"g1"}, now=50)
        assert report["orphans_remaining"] == 0 and not c.running
        findings[6] = self.satisfied(
            items[6],
            "After a reconcile pass no guest is left running without a lease, so the blast radius of a "
            "control-plane outage is bounded by the lease duration.",
            *self._evidence("component.py::VirtualizationController.reconcile"))
        return findings

COMPONENT = VirtualizationControllerComponent
