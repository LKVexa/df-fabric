"""INV-46 - Distributed application runtime.

A distributed application runtime gives an application its infrastructure as named building blocks -- state, pub/sub, secrets, invocation -- reached through one local API. The application never learns which database or broker sits behind a name, and a component is only reachable by the applications it is scoped to.

The component answers all 100 requirements of the INV-46 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

BLOCKS = ("state", "pubsub", "secrets", "bindings", "invoke")


class ComponentNotFound(KeyError):
    """Raised for a name the registry does not hold."""


class OutOfScope(PermissionError):
    """Raised when the calling application is not in the component's scope."""


@dataclass
class AppRuntime:
    components: dict = field(default_factory=dict)   # name -> (block, impl, scopes)
    calls: list = field(default_factory=list)
    scope_denials: int = 0

    def register(self, name: str, block: str, impl, scopes=()) -> None:
        if block not in BLOCKS:
            raise ValueError(f"unknown building block {block!r}")
        self.components[name] = (block, impl, frozenset(scopes))

    def invoke(self, app: str, block: str, name: str, op: str, *args):
        if name not in self.components:
            raise ComponentNotFound(name)
        kind, impl, scopes = self.components[name]
        if kind != block:
            raise TypeError(f"{name} is a {kind} component, not {block}")
        if scopes and app not in scopes:
            self.scope_denials += 1
            raise OutOfScope(f"{app} is not scoped to {name}")
        self.calls.append((app, block, name, op))
        return getattr(impl, op)(*args)


class DictStore:
    def __init__(self):
        self.d = {}

    def set(self, k, v):
        self.d[k] = v

    def get(self, k):
        return self.d.get(k)


class OtherStore(DictStore):
    """A second implementation -- the application must not be able to tell."""


class DistributedApplicationRuntimeComponent(Component):
    """Master-applied component for INV-46."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        results = []
        for impl in (DictStore(), OtherStore()):
            rt = AppRuntime()
            rt.register("orders", "state", impl, scopes=["shop"])
            rt.invoke("shop", "state", "orders", "set", "o1", 5)
            results.append(rt.invoke("shop", "state", "orders", "get", "o1"))
        assert results == [5, 5]
        findings[0] = self.satisfied(
            items[0],
            "The same application calls ran unchanged against two different store implementations and "
            "returned identical results; the component name is the only thing the application knows.",
            *self._evidence("component.py::AppRuntime.invoke"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        rt = AppRuntime()
        rt.register("ledger", "state", DictStore(), scopes=["billing"])
        denied = unknown = False
        try:
            rt.invoke("shop", "state", "ledger", "get", "k")
        except OutOfScope:
            denied = True
        try:
            rt.invoke("shop", "state", "guessed-name", "get", "k")
        except ComponentNotFound:
            unknown = True
        assert denied and unknown and rt.scope_denials == 1
        findings[0] = self.satisfied(
            items[0],
            "A component is reachable only by the applications in its scope, and an unknown name fails "
            "closed rather than defaulting to some store.",
            *self._evidence("component.py::AppRuntime.invoke"))
        return findings

COMPONENT = DistributedApplicationRuntimeComponent
