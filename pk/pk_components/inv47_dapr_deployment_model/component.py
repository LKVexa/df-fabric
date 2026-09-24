"""INV-47 - Dapr deployment model.

The deployment model decides where the application runtime lives relative to the application: a sidecar beside each instance, one shared agent per node, or embedded in-process. Each trades isolation against density, and the model's job is to make that trade explicit, give every application exactly one reachable runtime, and keep the runtime within a supported version of its control plane.

The component answers all 100 requirements of the INV-47 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

MODES = {"sidecar": "per-instance", "per-node": "shared", "embedded": "in-process"}
MAX_MINOR_SKEW = 1


class BindingError(RuntimeError):
    """Raised when an instance would have zero or two runtimes."""


class SkewExceeded(RuntimeError):
    """Raised when a runtime is too far behind its control plane."""


def within_skew(control: str, runtime: str) -> bool:
    cmaj, cmin = (int(x) for x in control.split(".")[:2])
    rmaj, rmin = (int(x) for x in runtime.split(".")[:2])
    return cmaj == rmaj and 0 <= cmin - rmin <= MAX_MINOR_SKEW


@dataclass
class Deployment:
    control_version: str
    bindings: dict = field(default_factory=dict)     # instance -> (runtime_id, mode, tenant)
    node_tenants: dict = field(default_factory=dict)

    def bind(self, instance: str, runtime_id: str, mode: str, version: str, tenant: str, node: str):
        if mode not in MODES:
            raise ValueError(mode)
        if instance in self.bindings:
            raise BindingError(f"{instance} already bound to {self.bindings[instance][0]}")
        if not within_skew(self.control_version, version):
            raise SkewExceeded(f"runtime {version} vs control {self.control_version}")
        if mode == "per-node":
            seen = self.node_tenants.setdefault(node, tenant)
            if seen != tenant:
                raise BindingError(f"per-node runtime on {node} already serves tenant {seen}")
        self.bindings[instance] = (runtime_id, mode, tenant)

    def unbind(self, instance: str) -> None:
        self.bindings.pop(instance, None)

    def reachable(self, instance: str) -> str:
        if instance not in self.bindings:
            raise BindingError(f"{instance} has no runtime")
        return self.bindings[instance][0]


class DaprDeploymentModelComponent(Component):
    """Master-applied component for INV-47."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        d = Deployment("1.14")
        d.bind("app-1", "rt-1", "sidecar", "1.14", "acme", "n1")
        twice = False
        try:
            d.bind("app-1", "rt-2", "sidecar", "1.14", "acme", "n1")
        except BindingError:
            twice = True
        d.unbind("app-1")
        gone = False
        try:
            d.reachable("app-1")
        except BindingError:
            gone = True
        assert twice and gone
        findings[0] = self.satisfied(
            items[0],
            "Each instance binds to exactly one runtime: a second binding is refused, and once the "
            "application is unbound its runtime is no longer reachable rather than lingering as an orphan.",
            *self._evidence("component.py::Deployment.bind"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        d = Deployment("1.14")
        d.bind("a", "rt-n1", "per-node", "1.14", "acme", "n1")
        shared = False
        try:
            d.bind("b", "rt-n1", "per-node", "1.14", "globex", "n1")
        except BindingError:
            shared = True
        assert shared
        findings[0] = self.satisfied(
            items[0],
            "The density mode cannot erase isolation: a shared per-node runtime is refused for a second "
            "tenant on the same node, so tenants that need separation are pushed to sidecars.",
            *self._evidence("component.py::Deployment.bind", "component.py::MODES"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        assert within_skew("1.14", "1.13") and not within_skew("1.14", "1.12")
        assert not within_skew("2.0", "1.14")
        findings[0] = self.satisfied(
            items[0],
            f"Runtime upgrades are gated by a skew bound of {MAX_MINOR_SKEW} minor version: 1.13 is "
            "accepted against a 1.14 control plane, 1.12 and any major mismatch are refused.",
            *self._evidence("component.py::within_skew"))
        return findings

COMPONENT = DaprDeploymentModelComponent
