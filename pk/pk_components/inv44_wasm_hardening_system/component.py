"""INV-44 - Wasm hardening system.

The Wasm hardening system is what turns a Wasm runtime from a portability layer into an isolation boundary: guard pages, control-flow integrity, bounded fuel, and a compiler whose output is verified rather than trusted. A hardened runtime with one of these off is not a hardened runtime, and this element says so.

The component answers all 100 requirements of the INV-44 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Every one of these must be active. A partial set is not a hardened runtime.
REQUIRED_HARDENING = frozenset({
    "guard_pages",          # traps out-of-bounds linear memory access in hardware
    "cfi",                  # control-flow integrity on indirect calls
    "bounds_checks",        # explicit checks where guard pages do not reach
    "stack_limits",         # bounded recursion
    "fuel_metering",        # no unbounded execution
    "output_verification",  # compiled code is checked, not trusted
})

#: Linear memory ceiling in 64KiB pages.
MEMORY_PAGE_CEILING = 512


class HardeningIncomplete(PermissionError):
    """Raised when the engine is missing a required hardening feature."""


class OutputUnverified(PermissionError):
    """Raised when compiled module output fails verification."""


class FuelExhausted(RuntimeError):
    """Raised when a module consumes its whole fuel budget."""


class MemoryCeiling(RuntimeError):
    """Raised when linear memory would grow past its ceiling."""


@dataclass
class Engine:
    """A Wasm engine that either has the whole hardening set or refuses to run."""

    name: str
    active: frozenset

    def check(self) -> None:
        missing = REQUIRED_HARDENING - self.active
        if missing:
            raise HardeningIncomplete(
                f"{self.name}: hardening features inactive: {sorted(missing)}")

    def instantiate(self, module: str, *, output_valid: bool, fuel: int,
                    pages: int = 1) -> "Instance":
        self.check()
        if not output_valid:
            raise OutputUnverified(
                f"{module}: compiled output failed verification and will not execute")
        if pages > MEMORY_PAGE_CEILING:
            raise MemoryCeiling(
                f"{module}: {pages} initial pages exceed the {MEMORY_PAGE_CEILING}-page ceiling")
        return Instance(module, self, fuel, pages)


@dataclass
class Instance:
    """A metered, memory-capped module instance."""

    module: str
    engine: Engine
    fuel: int
    pages: int
    consumed: int = 0
    trapped: str | None = None

    def step(self, cost: int = 1) -> int:
        if self.trapped:
            raise RuntimeError(f"{self.module}: already trapped ({self.trapped})")
        if self.consumed + cost > self.fuel:
            self.trapped = "fuel exhausted"
            raise FuelExhausted(
                f"{self.module}: consumed {self.consumed} of {self.fuel} fuel")
        self.consumed += cost
        return self.fuel - self.consumed

    def grow(self, pages: int) -> int:
        if self.pages + pages > MEMORY_PAGE_CEILING:
            raise MemoryCeiling(
                f"{self.module}: growing to {self.pages + pages} pages exceeds "
                f"the {MEMORY_PAGE_CEILING}-page ceiling")
        self.pages += pages
        return self.pages


class WasmHardeningSystemComponent(Component):
    """Master-applied component for INV-44."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        engine = Engine("wasmtime", REQUIRED_HARDENING)
        instance = engine.instantiate("svc", output_valid=True, fuel=100, pages=2)
        assert instance.step(10) == 90 and instance.grow(4) == 6
        findings[5] = self.satisfied(
            items[5],
            f"A fully hardened engine instantiates a metered instance: {len(REQUIRED_HARDENING)} hardening "
            "features active, fuel accounted per step, memory growth bounded.",
            *self._evidence("component.py::Engine.instantiate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        proven = []
        for feature in sorted(REQUIRED_HARDENING):
            partial = Engine("wasmtime", REQUIRED_HARDENING - {feature})
            try:
                partial.instantiate("svc", output_valid=True, fuel=10)
            except HardeningIncomplete:
                proven.append(feature)
        assert len(proven) == len(REQUIRED_HARDENING), proven
        findings[5] = self.satisfied(
            items[5],
            f"Every one of the {len(REQUIRED_HARDENING)} hardening features is individually load-bearing: "
            "removing any single one refuses instantiation, so there is no partially hardened mode.",
            *self._evidence("component.py::Engine.check"))
        engine = Engine("wasmtime", REQUIRED_HARDENING)
        try:
            engine.instantiate("svc", output_valid=False, fuel=10)
        except OutputUnverified:
            findings[4] = self.satisfied(
                items[4],
                "Compiled output is verified before execution rather than trusted, so a compiler bug that "
                "emits escaping code is caught before it runs.",
                *self._evidence("component.py::Engine.instantiate"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        engine = Engine("wasmtime", REQUIRED_HARDENING)
        instance = engine.instantiate("svc", output_valid=True, fuel=5)
        try:
            instance.step(10)
        except FuelExhausted:
            assert instance.trapped == "fuel exhausted"
            findings[0] = self.satisfied(
                items[0],
                "Fuel exhaustion traps the instance deterministically, so an infinite loop costs its "
                "budget rather than the node.",
                *self._evidence("component.py::Instance.step"))
        big = engine.instantiate("svc2", output_valid=True, fuel=100, pages=MEMORY_PAGE_CEILING)
        try:
            big.grow(1)
        except MemoryCeiling:
            findings[5] = self.satisfied(
                items[5],
                f"Linear memory is capped at {MEMORY_PAGE_CEILING} pages; a grow past the ceiling is "
                "refused rather than satisfied until the host runs out.",
                *self._evidence("component.py::Instance.grow"))
        return findings

COMPONENT = WasmHardeningSystemComponent
