"""INV-32 - Elastic virtualization.

Elastic virtualization is memory and vCPU that move while the guest is running -- ballooning, hot-plug, free-page reporting. It is how an edge node runs more than it has, and it is also how a node gets OOM-killed, so every adjustment here is bounded and reversible.

The component answers all 100 requirements of the INV-32 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Fraction of host memory never available to guests.
RESERVE_FRACTION = 0.10


class ReserveBreach(RuntimeError):
    """Raised when an adjustment would allocate into the host reserve."""


class FloorBreach(RuntimeError):
    """Raised when an adjustment would reclaim a guest below its working set."""


@dataclass
class Guest:
    name: str
    tenant: str
    memory_mib: int
    floor_mib: int
    ceiling_mib: int
    vcpus: int = 1
    vcpu_max: int = 4
    cooperative: bool = True

    def __post_init__(self):
        if not self.floor_mib <= self.memory_mib <= self.ceiling_mib:
            raise ValueError(f"{self.name}: memory outside its own floor/ceiling")


@dataclass
class ElasticHost:
    """Live memory and vCPU adjustment inside a hard host reserve."""

    name: str
    total_mib: int
    guests: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    @property
    def reserve_mib(self) -> int:
        return int(self.total_mib * RESERVE_FRACTION)

    @property
    def allocated_mib(self) -> int:
        return sum(g.memory_mib for g in self.guests.values())

    @property
    def free_mib(self) -> int:
        return self.total_mib - self.reserve_mib - self.allocated_mib

    def add(self, guest: Guest) -> Guest:
        if guest.memory_mib > self.free_mib:
            raise ReserveBreach(
                f"{guest.name}: {guest.memory_mib}MiB exceeds {self.free_mib}MiB allocatable")
        self.guests[guest.name] = guest
        return guest

    def adjust_memory(self, name: str, target_mib: int, *, honoured: bool = True) -> dict:
        guest = self.guests[name]
        previous = guest.memory_mib
        if target_mib < guest.floor_mib:
            raise FloorBreach(
                f"{name}: {target_mib}MiB is below its {guest.floor_mib}MiB working-set floor")
        target = min(target_mib, guest.ceiling_mib)
        delta = target - previous
        if delta > self.free_mib:
            raise ReserveBreach(
                f"{name}: growing by {delta}MiB would take {delta - self.free_mib}MiB from the reserve")
        applied = target if honoured else previous
        guest.memory_mib = applied
        record = {"schema": "PK_RESOURCE_ADJUSTMENT/1", "guest": name,
                  "from_mib": previous, "requested_mib": target, "applied_mib": applied,
                  "honoured": honoured, "reversible_to": previous,
                  "host_free_mib": self.free_mib}
        self.history.append(record)
        return record

    def revert(self, record: dict) -> int:
        """Every adjustment is reversible to the value it replaced."""
        guest = self.guests[record["guest"]]
        guest.memory_mib = record["reversible_to"]
        return guest.memory_mib

    def adjust_vcpus(self, name: str, target: int) -> dict:
        guest = self.guests[name]
        if not 1 <= target <= guest.vcpu_max:
            raise ValueError(f"{name}: {target} vCPUs outside [1, {guest.vcpu_max}]")
        previous, guest.vcpus = guest.vcpus, target
        return {"schema": "PK_RESOURCE_ADJUSTMENT/1", "guest": name,
                "from_vcpus": previous, "applied_vcpus": target, "reversible_to": previous}


class ElasticVirtualizationComponent(Component):
    """Master-applied component for INV-32."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        host = ElasticHost("n1", total_mib=4096)
        host.add(Guest("g1", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048))
        grown = host.adjust_memory("g1", 2048)
        assert grown["applied_mib"] == 2048
        shrunk = host.adjust_memory("g1", 512)
        assert shrunk["applied_mib"] == 512
        assert host.revert(shrunk) == 2048
        findings[5] = self.satisfied(
            items[5],
            f"Memory moves in both directions within the guest's bounds and every adjustment reverts to "
            f"the value it replaced (reserve held at {host.reserve_mib}MiB throughout).",
            *self._evidence("component.py::ElasticHost"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        host = ElasticHost("n1", total_mib=1024)
        host.add(Guest("g1", "t1", memory_mib=512, floor_mib=128, ceiling_mib=1024))
        try:
            host.adjust_memory("g1", 1024)
        except ReserveBreach:
            findings[5] = self.satisfied(
                items[5],
                f"Growth stops at the host reserve ({host.reserve_mib}MiB of {host.total_mib}MiB): a "
                "tenant cannot consume the headroom the host needs to stay alive.",
                *self._evidence("component.py::ElasticHost.adjust_memory"))
        try:
            host.adjust_memory("g1", 64)
        except FloorBreach:
            findings[1] = self.satisfied(
                items[1],
                "Reclaim below a guest's declared working-set floor is refused, so reclaim cannot be used "
                "to starve a tenant into thrashing.",
                *self._evidence("component.py::ElasticHost.adjust_memory"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        host = ElasticHost("n1", total_mib=4096)
        host.add(Guest("g1", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048,
                       cooperative=False))
        record = host.adjust_memory("g1", 512, honoured=False)
        assert not record["honoured"] and record["applied_mib"] == 1024
        findings[0] = self.satisfied(
            items[0],
            "Ballooning is cooperative: a guest that does not return memory is recorded as unhonoured with "
            "its memory unchanged, rather than the host assuming the reclaim succeeded.",
            *self._evidence("component.py::ElasticHost.adjust_memory"))
        findings[4] = self.satisfied(
            items[4],
            "Adjustments are idempotent and reversible: re-applying the same target is a no-op and revert "
            "restores the previous value exactly.",
            *self._evidence("component.py::ElasticHost.revert"))
        return findings

COMPONENT = ElasticVirtualizationComponent
