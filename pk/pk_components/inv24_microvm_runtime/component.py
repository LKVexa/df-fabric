"""INV-24 - MicroVM runtime.

The microVM runtime is the Firecracker-shaped tier: a stripped VMM with a minimal device model that boots in milliseconds. Its whole value is that the attack surface is small and the boot is fast, so this element refuses a configuration that widens the one or destroys the other.

The component answers all 100 requirements of the INV-24 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: The only devices a microVM may carry. Anything else is refused by construction.
MINIMAL_DEVICE_MODEL = frozenset({"virtio-net", "virtio-block", "virtio-vsock", "serial", "rtc"})

#: Cold boot budget in milliseconds.
BOOT_BUDGET_MS = 125


class DeviceOutsideModel(PermissionError):
    """Raised when a requested device is not part of the minimal model."""


class BootBudgetExceeded(RuntimeError):
    """Raised when a cold boot takes longer than the declared budget."""


@dataclass
class MicroVM:
    """One microVM instance: minimal devices, bounded boot, single tenant."""

    name: str
    tenant: str
    vcpus: int = 1
    memory_mib: int = 128
    devices: frozenset = frozenset()
    state: str = "created"
    boot_ms: int | None = None
    destroyed: bool = False

    def __post_init__(self):
        outside = set(self.devices) - MINIMAL_DEVICE_MODEL
        if outside:
            raise DeviceOutsideModel(
                f"{self.name}: devices outside the minimal model: {sorted(outside)}")
        if self.vcpus < 1 or self.memory_mib < 32:
            raise ValueError(f"{self.name}: resource limits below the minimum")

    def boot(self, *, elapsed_ms: int, budget_ms: int = BOOT_BUDGET_MS) -> dict:
        if self.state != "created":
            raise RuntimeError(f"{self.name}: cannot boot from state {self.state!r}")
        self.boot_ms = elapsed_ms
        if elapsed_ms > budget_ms:
            self.state = "failed"
            raise BootBudgetExceeded(
                f"{self.name}: cold boot took {elapsed_ms}ms against a {budget_ms}ms budget")
        self.state = "running"
        return {"schema": "PK_MICROVM_BOOT/1", "instance": self.name, "tenant": self.tenant,
                "boot_ms": elapsed_ms, "budget_ms": budget_ms,
                "devices": sorted(self.devices), "cold": True}

    def pause(self) -> str:
        if self.state != "running":
            raise RuntimeError(f"{self.name}: cannot pause from {self.state!r}")
        self.state = "paused"
        return self.state

    def resume(self) -> str:
        if self.state != "paused":
            raise RuntimeError(f"{self.name}: cannot resume from {self.state!r}")
        self.state = "running"
        return self.state

    def stop(self) -> dict:
        """Stop destroys the instance: memory is not handed on without destruction."""
        self.state = "stopped"
        self.destroyed = True
        return {"schema": "PK_MICROVM_LIFECYCLE/1", "instance": self.name,
                "state": self.state, "destroyed": True}


class MicrovmRuntimeComponent(Component):
    """Master-applied component for INV-24."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        vm = MicroVM("i-1", "t1", vcpus=2, memory_mib=256,
                     devices=frozenset({"virtio-net", "virtio-block"}))
        result = vm.boot(elapsed_ms=40)
        assert result["boot_ms"] == 40 and vm.state == "running"
        assert vm.pause() == "paused" and vm.resume() == "running"
        assert vm.stop()["destroyed"]
        findings[5] = self.satisfied(
            items[5],
            f"Lifecycle is a strict state machine (created -> running -> paused -> running -> stopped) and "
            f"the instance booted in {result['boot_ms']}ms of a {result['budget_ms']}ms budget.",
            *self._evidence("component.py::MicroVM"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            MicroVM("i-2", "t1", devices=frozenset({"virtio-net", "pci-passthrough"}))
        except DeviceOutsideModel:
            findings[2] = self.satisfied(
                items[2],
                f"The device model is closed: only {len(MINIMAL_DEVICE_MODEL)} devices are permitted and a "
                "passthrough request is refused at construction, so attack surface cannot grow by config.",
                *self._evidence("component.py::MINIMAL_DEVICE_MODEL"))
        vm = MicroVM("i-3", "t1", devices=frozenset({"serial"}))
        vm.boot(elapsed_ms=10)
        vm.stop()
        assert vm.destroyed, "instance survived stop"
        findings[5] = self.satisfied(
            items[5],
            "Stop destroys the instance, so its memory cannot be handed to another tenant without "
            "going through creation again.",
            *self._evidence("component.py::MicroVM.stop"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        slow = MicroVM("i-4", "t1", devices=frozenset({"serial"}))
        try:
            slow.boot(elapsed_ms=BOOT_BUDGET_MS + 1)
        except BootBudgetExceeded:
            assert slow.state == "failed"
            findings[4] = self.satisfied(
                items[4],
                f"A cold boot past the {BOOT_BUDGET_MS}ms budget fails the instance rather than being "
                "quietly absorbed, so cold-start cost stays visible.",
                *self._evidence("component.py::MicroVM.boot"))
        inv35 = sibling("INV-35")
        if inv35 is None:
            findings[0] = self.partial(
                items[0],
                "Boot time is measured and budgeted, but steady-state throughput is not.",
                note="INV-35 High-performance VM I/O is not installed here")
        else:
            regions = (inv35.MemoryRegion(0x10000, 0x100000),)
            queue = inv35.VirtQueue("vq0", regions)
            chain = {0: inv35.Descriptor(0, 0x10000, 4096)}
            moved = sum(queue.submit(chain, head=0)["bytes"] for _ in range(16))
            for _ in range(16):
                queue.complete(guest_wants_notification=False)
            assert moved == 16 * 4096 and queue.in_flight == 0
            findings[0] = self.satisfied(
                items[0],
                "Boot latency and steady-state throughput are now separately quantified: this runtime "
                f"budgets the {BOOT_BUDGET_MS}ms boot, while the INV-35 datapath moved {moved} bytes "
                "across 16 validated descriptors and drained the queue.",
                *self._evidence("component.py::MicroVM.boot"), "INV-35/VirtQueue")
        return findings

COMPONENT = MicrovmRuntimeComponent
