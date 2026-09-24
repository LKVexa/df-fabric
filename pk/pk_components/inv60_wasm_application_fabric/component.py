"""INV-60 - Wasm application fabric.

A Wasm application fabric runs components across a lattice of hosts and wires them to capability providers by link name at run time. A component says 'I need a key-value store'; the fabric links it to one, routes calls across hosts, and restarts it elsewhere if a host goes. Artifacts are content-addressed, so what runs is exactly what was signed.

The component answers all 100 requirements of the INV-60 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field


class DigestMismatch(ValueError):
    pass


class NotLinked(PermissionError):
    pass


@dataclass
class Lattice:
    hosts: list
    registry: dict = field(default_factory=dict)       # ref -> bytes
    instances: dict = field(default_factory=dict)      # component -> host
    links: dict = field(default_factory=dict)          # (component, link) -> provider callable
    failovers: int = 0

    def push(self, data: bytes) -> str:
        ref = "sha256:" + hashlib.sha256(data).hexdigest()
        self.registry[ref] = data
        return ref

    def start(self, component: str, ref: str) -> str:
        data = self.registry[ref]
        if "sha256:" + hashlib.sha256(data).hexdigest() != ref:
            raise DigestMismatch(f"{component}: registry bytes do not match {ref[:19]}...")
        host = self.hosts[len(self.instances) % len(self.hosts)]
        self.instances[component] = host
        return host

    def link(self, component: str, name: str, provider) -> None:
        self.links[(component, name)] = provider

    def call(self, component: str, name: str, *args):
        if component not in self.instances:
            raise LookupError(f"{component} not running")
        provider = self.links.get((component, name))
        if provider is None:
            raise NotLinked(f"{component} has no link {name!r}")
        return provider(*args)

    def lose_host(self, host: str) -> list:
        self.hosts.remove(host)
        moved = [c for c, h in self.instances.items() if h == host]
        for i, c in enumerate(moved):
            self.instances[c] = self.hosts[i % len(self.hosts)]
            self.failovers += 1
        return moved


class WasmApplicationFabricComponent(Component):
    """Master-applied component for INV-60."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        lat = Lattice(["h1", "h2"])
        ref = lat.push(b"component-bytes-v1")
        lat.start("api", ref)
        lat.registry[ref] = b"tampered-bytes"
        tampered = False
        try:
            lat.start("api-2", ref)
        except DigestMismatch:
            tampered = True
        unlinked = False
        try:
            lat.call("api", "keyvalue", "get", "k")
        except NotLinked:
            unlinked = True
        assert tampered and unlinked
        findings[0] = self.satisfied(
            items[0],
            "Components are started only from bytes that hash to their reference -- swapped registry "
            "content is refused -- and a component can use only the capabilities it has been linked to.",
            *self._evidence("component.py::Lattice.start", "component.py::Lattice.call"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        lat = Lattice(["h1", "h2", "h3"])
        for i in range(6):
            lat.start(f"c{i}", lat.push(f"c{i}".encode()))
        kv = {}
        lat.link("c0", "keyvalue", lambda op, k, v=None: kv.__setitem__(k, v) if op == "set" else kv.get(k))
        victim = lat.instances["c0"]
        moved = lat.lose_host(victim)
        lat.call("c0", "keyvalue", "set", "a", 1)
        assert len(moved) == 2 and victim not in lat.instances.values() and lat.call("c0", "keyvalue", "get", "a") == 1
        findings[0] = self.satisfied(
            items[0],
            f"Losing a host reschedules its {len(moved)} components onto survivors, and their provider "
            "links survive the move, so callers keep working without re-linking.",
            *self._evidence("component.py::Lattice.lose_host"))
        return findings

COMPONENT = WasmApplicationFabricComponent
