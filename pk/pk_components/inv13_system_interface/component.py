"""INV-13 - System interface.

The system interface is WASI: the component's only door to the outside world. Nothing is ambient -- no implicit filesystem, no implicit clock, no implicit network. A component gets exactly the preopened handles its world declared, and asks for anything else in vain.

The component answers all 100 requirements of the INV-13 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import posixpath
from dataclasses import dataclass, field

#: Capabilities a world may grant. There is no default set.
CAPABILITIES = frozenset({
    "filesystem", "wall-clock", "monotonic-clock", "random",
    "sockets", "environment", "stdio", "http-outgoing",
})


class CapabilityDenied(PermissionError):
    """Raised when a component asks for something its world did not grant."""


class PathEscape(PermissionError):
    """Raised when a path would resolve outside its preopened directory."""


@dataclass(frozen=True)
class World:
    """What a component is allowed to see. Nothing outside this exists for it."""

    name: str
    capabilities: frozenset

    def __post_init__(self):
        unknown = set(self.capabilities) - CAPABILITIES
        if unknown:
            raise ValueError(f"unknown capabilities in world: {sorted(unknown)}")


@dataclass
class Instance:
    """A component instantiated against a world, with explicit preopens."""

    component: str
    world: World
    preopens: dict = field(default_factory=dict)      # logical root -> host root
    denials: list = field(default_factory=list)

    def grant_preopen(self, logical: str, host_root: str) -> dict:
        if "filesystem" not in self.world.capabilities:
            raise CapabilityDenied(
                f"{self.component}: world {self.world.name!r} grants no filesystem")
        self.preopens[logical] = host_root
        return {"schema": "PK_PREOPEN/1", "logical": logical, "host_root": host_root}

    def use(self, capability: str):
        """There is no default: a capability absent from the world simply is not there."""
        if capability not in self.world.capabilities:
            self.denials.append(capability)
            raise CapabilityDenied(
                f"{self.component}: {capability!r} is not in world {self.world.name!r}")
        return {"schema": "PK_WORLD/1", "component": self.component,
                "capability": capability, "granted": True}

    def resolve(self, logical_root: str, path: str) -> dict:
        """Resolve a path inside a preopen. Absolute paths and escapes are refused."""
        self.use("filesystem")
        if logical_root not in self.preopens:
            raise CapabilityDenied(
                f"{self.component}: no preopen for root {logical_root!r}")
        if path.startswith("/"):
            raise PathEscape(f"{path!r}: absolute paths are never resolved")
        host_root = self.preopens[logical_root]
        # normpath collapses '..' so an escape becomes visible rather than executed.
        candidate = posixpath.normpath(posixpath.join(host_root, path))
        root = posixpath.normpath(host_root)
        if candidate != root and not candidate.startswith(root + "/"):
            raise PathEscape(f"{path!r} escapes preopen {logical_root!r} ({candidate})")
        return {"schema": "PK_PATH_RESOLVE/1", "root": logical_root,
                "requested": path, "resolved": candidate, "inside_preopen": True}


class SystemInterfaceComponent(Component):
    """Master-applied component for INV-13."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        world = World("svc", frozenset({"filesystem", "monotonic-clock", "stdio"}))
        inst = Instance("api", world)
        inst.grant_preopen("/data", "/srv/tenant-a/data")
        ok = inst.resolve("/data", "reports/q3.csv")
        assert ok["resolved"] == "/srv/tenant-a/data/reports/q3.csv"
        assert inst.use("monotonic-clock")["granted"]
        findings[5] = self.satisfied(
            items[5],
            "A component sees exactly its world: three capabilities granted, one preopen, and a relative "
            "path resolved inside it.",
            *self._evidence("component.py::Instance"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        inst = Instance("api", World("svc", frozenset({"filesystem"})))
        inst.grant_preopen("/data", "/srv/tenant-a/data")
        proven = []
        for label, path in [("traversal", "../../etc/passwd"),
                            ("absolute", "/etc/passwd"),
                            ("nested traversal", "reports/../../../root/.ssh/id_rsa")]:
            try:
                inst.resolve("/data", path)
            except PathEscape:
                proven.append(label)
        assert len(proven) == 3, proven
        findings[2] = self.satisfied(
            items[2],
            f"Three path-confinement bypasses are refused ({', '.join(proven)}): resolution normalises "
            "first and compares against the preopen root, so '..' is visible rather than followed.",
            *self._evidence("component.py::Instance.resolve"))
        try:
            inst.use("sockets")
        except CapabilityDenied:
            findings[5] = self.satisfied(
                items[5],
                "A capability absent from the world is denied outright: there is no default environment "
                "to fall back on, so ambient authority has no entry point.",
                *self._evidence("component.py::Instance.use"))
        try:
            Instance("api", World("empty", frozenset())).grant_preopen("/d", "/srv")
        except CapabilityDenied:
            findings[1] = self.satisfied(
                items[1],
                "A world without the filesystem capability cannot be given a preopen at all, so least "
                "privilege holds at instantiation rather than at first use.",
                *self._evidence("component.py::Instance.grant_preopen"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        inst = Instance("api", World("svc", frozenset({"filesystem"})))
        try:
            inst.resolve("/nowhere", "x")
        except CapabilityDenied:
            findings[0] = self.satisfied(
                items[0],
                "Resolving against a root with no preopen is a named denial, not a silent fallback to "
                "the host filesystem root.",
                *self._evidence("component.py::Instance.resolve"))
        try:
            World("bad", frozenset({"filesystem", "gpu-direct"}))
        except ValueError:
            findings[6] = self.satisfied(
                items[6],
                "A world naming a capability outside the defined set is refused at construction, so the "
                "surface cannot be widened by inventing a capability name.",
                *self._evidence("component.py::World"))
        return findings

COMPONENT = SystemInterfaceComponent
