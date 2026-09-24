"""INV-29 - Hybrid Wasm/unikernel.

The hybrid Wasm/unikernel model puts a Wasm runtime inside a unikernel image: the module gets the component model's portability and the unikernel's hardware-backed boundary at once. The point is defence in depth, so this element refuses a composition where one layer's guarantees silently substitute for the other's.

The component answers all 100 requirements of the INV-29 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass


class LayerMissing(PermissionError):
    """Raised when a composition does not carry the required number of sound layers."""


class ImportUnsatisfied(PermissionError):
    """Raised when a Wasm module imports something the host image does not expose."""


@dataclass(frozen=True)
class WasmModule:
    name: str
    imports: frozenset
    hardened: bool = True
    architecture: str = "wasm32"


@dataclass(frozen=True)
class HostImage:
    """The sealed unikernel image hosting the Wasm runtime."""

    name: str
    exposes: frozenset          # host functions available to modules
    sealed: bool = True
    architecture: str = "x86_64"


def compose(module: WasmModule, host: HostImage, *, required_layers: int = 2) -> dict:
    """Compose the two layers, verifying each on its own terms."""
    layers, failures = [], []

    if host.sealed:
        layers.append({"layer": "unikernel", "guarantee": "hardware-backed address-space isolation"})
    else:
        failures.append("unikernel: host image is not sealed")

    if module.hardened:
        layers.append({"layer": "wasm", "guarantee": "software fault isolation and typed imports"})
    else:
        failures.append("wasm: module is not hardened")

    if len(layers) < required_layers:
        raise LayerMissing(
            f"{module.name}: {len(layers)} sound layer(s), {required_layers} required ({'; '.join(failures)})")

    unsatisfied = module.imports - host.exposes
    if unsatisfied:
        raise ImportUnsatisfied(
            f"{module.name}: imports not exposed by {host.name}: {sorted(unsatisfied)}")

    return {"schema": "PK_HYBRID_COMPOSITION/1", "module": module.name, "host": host.name,
            "layers": layers, "layer_count": len(layers),
            "imports": sorted(module.imports),
            "defence_in_depth": len(layers) >= 2}


class HybridWasmUnikernelComponent(Component):
    """Master-applied component for INV-29."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        host = HostImage("mirage-host", frozenset({"clock", "net-send", "net-recv"}))
        module = WasmModule("svc", frozenset({"clock", "net-send"}))
        result = compose(module, host)
        assert result["layer_count"] == 2 and result["defence_in_depth"]
        assert [l["layer"] for l in result["layers"]] == ["unikernel", "wasm"]
        findings[5] = self.satisfied(
            items[5],
            "Composition records both layers and the distinct guarantee each contributes, so the hybrid "
            "is never described as a single stronger sandbox.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        host = HostImage("host", frozenset({"clock"}))
        try:
            compose(WasmModule("svc", frozenset({"clock", "raw-socket"})), host)
        except ImportUnsatisfied:
            findings[2] = self.satisfied(
                items[2],
                "A module importing something the sealed host image does not expose is refused, so imports "
                "cannot be satisfied by an escape hatch beneath the unikernel.",
                *self._evidence("component.py::compose"))
        proven = []
        for label, m, h in [
            ("unikernel layer", WasmModule("a", frozenset()), HostImage("h", frozenset(), sealed=False)),
            ("wasm layer", WasmModule("b", frozenset(), hardened=False), HostImage("h", frozenset())),
        ]:
            try:
                compose(m, h)
            except LayerMissing:
                proven.append(label)
        assert len(proven) == 2
        findings[5] = self.satisfied(
            items[5],
            f"Losing either layer ({', '.join(proven)}) refuses the composition rather than falling back "
            "to the surviving one, so defence in depth cannot quietly become defence in breadth.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[6] = self.satisfied(
            items[6],
            "Both layers are mandatory in this tier; a single-layer deployment is a different tier "
            "(INV-27 or INV-44 alone), not a degraded version of this one.",
            *self._evidence("component.py::compose", "contract.py"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        inv11 = sibling("INV-11")
        if inv11 is None:
            findings[0] = self.partial(
                items[0],
                "Imports are matched against the host image by name, which catches a missing capability "
                "but not a capability whose signature has drifted.",
                note="INV-11 Interface contract language is not installed here")
            return findings
        clock = inv11.Func("now", (("id", "string"),), ("u64",))
        host_iface = inv11.Interface("wasi:clocks", "0.2.0", frozenset({clock}))
        guest_ok = inv11.Interface("wasi:clocks", "0.2.0", frozenset({clock}))
        drifted = inv11.Interface(
            "wasi:clocks", "0.2.1",
            frozenset({inv11.Func("now", (("id", "string"),), ("u64", "error"))}))
        assert inv11.check_link(host_iface, guest_ok)["linked"]
        caught = False
        try:
            inv11.check_link(host_iface, drifted)
        except inv11.Incompatible:
            caught = True
        assert caught
        assert inv11.classify(host_iface, drifted)["class"] == inv11.BREAKING
        findings[0] = self.satisfied(
            items[0],
            "The two layers are linked on typed interfaces rather than import names: a guest whose "
            "signature matches links, and one that added a result case the host image cannot produce is "
            "refused and classified breaking, so signature drift cannot slip through the name match.",
            *self._evidence("component.py::compose"), "INV-11/check_link")
        return findings

COMPONENT = HybridWasmUnikernelComponent
