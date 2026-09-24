"""GAP-11 - Accelerator scheduling.

Accelerator scheduling treats a GPU or NPU as an exclusive, attestable resource rather than a divisible number. A device is either wholly assigned, partitioned into declared slices, or not available -- and a device is scrubbed between tenants before it is handed on.

The component answers all 100 requirements of the GAP-11 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class NoMatchingAccelerator(RuntimeError):
    """Raised when no free device satisfies the declared requirement."""


class ScrubRequired(PermissionError):
    """Raised when a device would move between tenants without a completed scrub."""


class UndeclaredPartition(ValueError):
    """Raised when a partition is requested that the device does not declare."""


@dataclass
class Accelerator:
    """One physical device, optionally carrying declared partitions."""

    device: str
    generation: str
    memory_gb: int
    features: frozenset = frozenset()
    partitions: tuple = ()          # declared partition names; empty means whole-device only
    holder: tuple | None = None     # (tenant, workload, partition)
    last_tenant: str | None = None
    scrubbed: bool = True

    @property
    def free(self) -> bool:
        return self.holder is None

    def matches(self, *, generation: str | None, memory_gb: int, features: frozenset) -> bool:
        if generation is not None and self.generation != generation:
            return False
        return self.memory_gb >= memory_gb and features <= self.features

    def scrub(self, *, succeeds: bool = True) -> dict:
        """Scrub device memory between tenants. A failed scrub quarantines the device."""
        self.scrubbed = bool(succeeds)
        return {"schema": "PK_SCRUB/1", "device": self.device,
                "completed": self.scrubbed,
                "quarantined": not self.scrubbed}


@dataclass
class AcceleratorPool:
    """Exclusive accelerator allocation with mandatory cross-tenant scrubbing."""

    devices: list = field(default_factory=list)

    def allocate(self, *, tenant: str, workload: str, memory_gb: int = 0,
                 generation: str | None = None, features=frozenset(),
                 partition: str | None = None) -> dict:
        features = frozenset(features)
        candidates = [d for d in self.devices
                      if d.free and d.matches(generation=generation, memory_gb=memory_gb,
                                              features=features)]
        if not candidates:
            raise NoMatchingAccelerator(
                f"{workload}: no free device with generation={generation} memory>={memory_gb}GB "
                f"features={sorted(features)}")
        device = min(candidates, key=lambda d: (d.memory_gb, d.device))   # smallest sufficient
        if partition is not None and partition not in device.partitions:
            raise UndeclaredPartition(
                f"{device.device} does not declare partition {partition!r}")
        if device.last_tenant is not None and device.last_tenant != tenant and not device.scrubbed:
            raise ScrubRequired(
                f"{device.device} last served {device.last_tenant}; scrub required before {tenant}")
        if not device.scrubbed:
            raise ScrubRequired(f"{device.device} is quarantined after a failed scrub")
        device.holder = (tenant, workload, partition)
        return {"schema": "PK_ACCELERATOR_ALLOCATION/1", "device": device.device,
                "tenant": tenant, "workload": workload, "partition": partition,
                "generation": device.generation, "memory_gb": device.memory_gb}

    def release(self, device_name: str) -> None:
        for device in self.devices:
            if device.device == device_name and device.holder is not None:
                device.last_tenant = device.holder[0]
                device.holder = None
                device.scrubbed = False       # dirty until explicitly scrubbed
                return

    def allocations(self) -> dict:
        return {d.device: d.holder for d in self.devices if d.holder is not None}


class AcceleratorSchedulingComponent(Component):
    """Master-applied component for GAP-11."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        pool = AcceleratorPool([
            Accelerator("gpu0", "gen9", 24, frozenset({"fp8"}), partitions=("half", "quarter")),
            Accelerator("gpu1", "gen9", 80, frozenset({"fp8", "nvlink"})),
        ])
        small = pool.allocate(tenant="t1", workload="w1", memory_gb=16, features={"fp8"})
        assert small["device"] == "gpu0", "did not choose the smallest sufficient device"
        big = pool.allocate(tenant="t1", workload="w2", memory_gb=64, features={"nvlink"})
        assert big["device"] == "gpu1"
        findings[5] = self.satisfied(
            items[5],
            "Allocation matches generation, memory and features and picks the smallest sufficient device, "
            "leaving larger accelerators for workloads that need them.",
            *self._evidence("component.py::AcceleratorPool.allocate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pool = AcceleratorPool([Accelerator("gpu0", "gen9", 24)])
        pool.allocate(tenant="t1", workload="w1")
        try:
            pool.allocate(tenant="t2", workload="w2")
        except NoMatchingAccelerator:
            findings[5] = self.satisfied(
                items[5],
                "An allocated device is invisible to another tenant's request: there is no path to "
                "concurrent cross-tenant allocation.",
                *self._evidence("component.py::AcceleratorPool.allocate"))
        pool.release("gpu0")
        try:
            pool.allocate(tenant="t2", workload="w2")
        except ScrubRequired:
            findings[2] = self.satisfied(
                items[2],
                "A released device is dirty by default: handing it to a different tenant is refused until "
                "a scrub completes, closing the residual-data path.",
                *self._evidence("component.py::AcceleratorPool.release"))
        pool.devices[0].scrub()
        assert pool.allocate(tenant="t2", workload="w2")["device"] == "gpu0"
        findings[6] = self.satisfied(
            items[6],
            "After a completed scrub the device serves the next tenant; the scrub is the gate, not a "
            "best-effort courtesy.",
            *self._evidence("component.py::Accelerator.scrub"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        pool = AcceleratorPool([Accelerator("gpu0", "gen9", 24, partitions=("half",))])
        try:
            pool.allocate(tenant="t1", workload="w", partition="third")
        except UndeclaredPartition:
            findings[6] = self.satisfied(
                items[6],
                "A partition the device does not declare cannot be allocated, so the scheduler cannot "
                "invent slices the hardware does not enforce.",
                *self._evidence("component.py::AcceleratorPool.allocate"))
        pool.allocate(tenant="t1", workload="w")
        pool.release("gpu0")
        result = pool.devices[0].scrub(succeeds=False)
        assert result["quarantined"]
        try:
            pool.allocate(tenant="t1", workload="w2")
        except ScrubRequired:
            findings[1] = self.satisfied(
                items[1],
                "A device whose scrub failed is quarantined and refused even to its previous tenant, "
                "degrading capacity rather than risking residue.",
                *self._evidence("component.py::Accelerator.scrub"))
        return findings

COMPONENT = AcceleratorSchedulingComponent
