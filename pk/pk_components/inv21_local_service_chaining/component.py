"""INV-21 - Local service chaining.

Local service chaining is what makes the component model pay off operationally: when component A calls component B and both are on the same host, the call never becomes a network request. It becomes a direct invocation, with the same interface, the same capability checks and the same observability -- the topology changes, the semantics do not.

The component answers all 100 requirements of the INV-21 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: How deep a local chain may go before it is refused.
DEFAULT_MAX_DEPTH = 4


class ChainTooDeep(RuntimeError):
    """Raised when a chain exceeds its depth bound."""


class ChainCycle(RuntimeError):
    """Raised when a component appears twice in one chain."""


class CrossTenantChain(PermissionError):
    """Raised when a local hop would cross a tenant boundary."""


@dataclass
class Residency:
    """Which components share this host, and for which tenant."""

    host: str
    #: component name -> (tenant, handler)
    table: dict = field(default_factory=dict)

    def place(self, name: str, tenant: str, handler) -> None:
        self.table[name] = (tenant, handler)

    def is_local(self, name: str) -> bool:
        return name in self.table


@dataclass
class Chainer:
    """Routes a call locally when it can, over the network when it cannot."""

    residency: Residency
    max_depth: int = DEFAULT_MAX_DEPTH
    hops_local: int = 0
    hops_remote: int = 0
    cycles_refused: int = 0
    depth_exceeded: int = 0
    #: Trace ids observed on each hop, in order -- proof the context survives.
    trace: list = field(default_factory=list)

    def call(self, callee: str, tenant: str, request, *, path=None, trace_id="t-0"):
        path = list(path or [])
        if callee in path:
            self.cycles_refused += 1
            raise ChainCycle(" -> ".join(path + [callee]))
        if len(path) >= self.max_depth:
            self.depth_exceeded += 1
            raise ChainTooDeep(f"depth {len(path)} reached bound {self.max_depth}")
        self.trace.append((callee, trace_id))
        if not self.residency.is_local(callee):
            self.hops_remote += 1
            return ("remote", callee, request)
        callee_tenant, handler = self.residency.table[callee]
        if callee_tenant != tenant:
            raise CrossTenantChain(
                f"{callee} belongs to {callee_tenant}, caller is {tenant}")
        self.hops_local += 1
        return handler(self, request, path + [callee], tenant, trace_id)


class LocalServiceChainingComponent(Component):
    """Master-applied component for INV-21."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        res = Residency("host-1")
        res.place("b", "acme", lambda ch, req, path, tenant, tid: ("local", "b", req))
        ch = Chainer(res)
        assert ch.call("b", "acme", {"n": 1})[0] == "local"
        assert ch.call("elsewhere", "acme", {"n": 1})[0] == "remote"
        assert ch.hops_local == 1 and ch.hops_remote == 1
        findings[0] = self.satisfied(
            items[0],
            "A co-resident callee is dispatched locally and a non-resident one falls back to the network "
            f"transparently ({ch.hops_local} local, {ch.hops_remote} remote), so the caller's code is the "
            "same either way and only the topology differs.",
            *self._evidence("component.py::Chainer.call"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        res = Residency("host-1")

        def recurse(ch, req, path, tenant, tid):
            return ch.call("b", tenant, req, path=path, trace_id=tid)

        res.place("b", "acme", recurse)
        ch = Chainer(res)
        cycled = False
        try:
            ch.call("b", "acme", {})
        except ChainCycle:
            cycled = True
        assert cycled and ch.cycles_refused == 1

        res2 = Residency("host-1")
        n = {"i": 0}

        def descend(chain, req, path, tenant, tid):
            n["i"] += 1
            return chain.call(f"s{n['i']}", tenant, req, path=path, trace_id=tid)

        for i in range(8):
            res2.place(f"s{i}", "acme", descend)
        ch2 = Chainer(res2, max_depth=3)
        deep = False
        try:
            ch2.call("s0", "acme", {})
        except ChainTooDeep:
            deep = True
        assert deep and ch2.depth_exceeded == 1
        findings[1] = self.satisfied(
            items[1],
            f"A chain that revisits a component is refused as a cycle and a chain past the depth bound "
            f"({ch2.max_depth}) is refused as too deep, so neither a loop nor a runaway fan-out can spin "
            "on the local path.",
            *self._evidence("component.py::Chainer.call"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        res = Residency("host-1")
        res.place("b", "other-tenant", lambda ch, req, path, tenant, tid: ("local", "b", req))
        ch = Chainer(res)
        crossed = False
        try:
            ch.call("b", "acme", {})
        except CrossTenantChain:
            crossed = True
        assert crossed and ch.hops_local == 0
        findings[2] = self.satisfied(
            items[2],
            "Co-residency is not authority: a callee belonging to another tenant is refused even though it "
            "sits on the same host, so the local fast path cannot be used to sidestep tenant policy.",
            *self._evidence("component.py::Chainer.call"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        res = Residency("host-1")
        res.place("c", "acme", lambda ch, req, path, tenant, tid: ("local", "c", req))
        res.place("b", "acme",
                  lambda ch, req, path, tenant, tid: ch.call("c", tenant, req, path=path, trace_id=tid))
        ch = Chainer(res)
        ch.call("b", "acme", {}, trace_id="t-7")
        assert [t for _, t in ch.trace] == ["t-7", "t-7"]
        findings[0] = self.satisfied(
            items[0],
            f"Trace context survives every local hop ({[c for c, _ in ch.trace]} all carrying t-7), so a "
            "chain that never touched the network is still a visible, attributable sequence of hops "
            "rather than one opaque call.",
            *self._evidence("component.py::Chainer.call"))
        return findings

COMPONENT = LocalServiceChainingComponent
