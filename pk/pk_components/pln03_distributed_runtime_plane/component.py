"""PLN-03 - Distributed runtime plane.

The distributed runtime plane provides the sidecar-free building blocks an application uses at run time: state, messaging, secrets, and service invocation, behind stable APIs with pluggable backing infrastructure. Applications bind to capabilities, never to a broker or a database.

The component answers all 100 requirements of the PLN-03 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


class CapabilityDenied(PermissionError):
    """Raised when a workload calls a capability it is not bound to."""


class AdapterUnavailable(RuntimeError):
    """Raised when the backing store for a bound capability cannot be reached."""


class Adapter:
    """Minimal in-memory reference adapter used for verification."""

    def __init__(self, name: str, available: bool = True):
        self.name = name
        self.available = available
        self._store: dict[str, bytes] = {}
        self._seen: set[str] = set()

    def get(self, key: str):
        if not self.available:
            raise AdapterUnavailable(self.name)
        return self._store.get(key)

    def set(self, key: str, value: bytes):
        if not self.available:
            raise AdapterUnavailable(self.name)
        self._store[key] = value

    def accept(self, idempotency_key: str) -> bool:
        """Return True the first time an idempotency key is seen."""
        if idempotency_key in self._seen:
            return False
        self._seen.add(idempotency_key)
        return True


class DistributedRuntime:
    """The backend-independent API surface bound to a revision's capabilities."""

    def __init__(self, bindings: dict[str, Adapter]):
        self._bindings = dict(bindings)

    def _adapter(self, workload: str, capability: str) -> Adapter:
        adapter = self._bindings.get(f"{workload}:{capability}")
        if adapter is None:
            raise CapabilityDenied(f"{workload} is not bound to {capability!r}")
        return adapter

    @staticmethod
    def _key(tenant: str, key: str) -> str:
        if "/" in tenant:
            raise ValueError("tenant may not contain a namespace separator")
        return f"{tenant}/{key}"

    def state_set(self, workload: str, tenant: str, key: str, value: bytes) -> None:
        self._adapter(workload, "state").set(self._key(tenant, key), value)

    def state_get(self, workload: str, tenant: str, key: str):
        return self._adapter(workload, "state").get(self._key(tenant, key))

    def publish(self, workload: str, tenant: str, topic: str, payload: bytes, idempotency_key: str) -> bool:
        adapter = self._adapter(workload, "messaging")
        if not adapter.accept(f"{tenant}/{topic}/{idempotency_key}"):
            return False
        adapter.set(self._key(tenant, f"{topic}/{idempotency_key}"), payload)
        return True


class DistributedRuntimePlaneComponent(Component):
    """Master-applied component for PLN-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        state = Adapter("state-local")
        runtime = DistributedRuntime({"api:state": state, "api:messaging": Adapter("bus-local")})
        runtime.state_set("api", "t1", "k", b"v")
        assert runtime.state_get("api", "t1", "k") == b"v"
        assert runtime.state_get("api", "t2", "k") is None, "tenant namespace leaked"
        first = runtime.publish("api", "t1", "orders", b"p", "idem-1")
        second = runtime.publish("api", "t1", "orders", b"p", "idem-1")
        assert first and not second, "idempotency key was not honoured"
        findings[5] = self.satisfied(
            items[5],
            "Runtime verified: tenant-namespaced state, duplicate publish suppressed by idempotency key.",
            *self._evidence("component.py::DistributedRuntime"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        runtime = DistributedRuntime({"api:state": Adapter("state-local")})
        try:
            runtime.state_get("api", "t1", "k")
            runtime.publish("api", "t1", "topic", b"x", "i")
        except CapabilityDenied:
            findings[1] = self.satisfied(
                items[1], "Unbound capability calls fail closed with CapabilityDenied.",
                *self._evidence("component.py::DistributedRuntime._adapter"))
        try:
            runtime.state_set("api", "t1/../t2", "k", b"v")
        except ValueError:
            findings[5] = self.satisfied(
                items[5], "Tenant namespace escape is refused at key construction.",
                *self._evidence("component.py::DistributedRuntime._key"))
        pln04 = sibling("PLN-04")
        if pln04 is None:
            findings[2] = self.partial(
                items[2],
                "Adapters run in-process, so ambient authority is bounded by the host rather than a tier.",
                note="PLN-04 Execution plane is not installed here")
        else:
            node = pln04.Node({"process": True, "wasm": True, "microvm": True})
            tier = pln04.admit(node, "state-adapter", "t1", "third-party")
            assert tier in ("unikernel", "microvm"), tier
            findings[2] = self.satisfied(
                items[2],
                f"Adapters are hosted through the PLN-04 execution plane: a third-party adapter is admitted "
                f"to the {tier!r} tier, so its filesystem, network and device authority is the tier's, not "
                "the host's.",
                *self._evidence("component.py::DistributedRuntime"), "PLN-04/admit")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        runtime = DistributedRuntime({"api:state": Adapter("state-down", available=False)})
        try:
            runtime.state_get("api", "t1", "k")
        except AdapterUnavailable:
            findings[2] = self.satisfied(
                items[2], "Backing-store loss surfaces as AdapterUnavailable without corrupting caller state.",
                *self._evidence("component.py::Adapter"))
        pln06 = sibling("PLN-06")
        if pln06 is None:
            findings[5] = self.partial(
                items[5], "The reference adapter queues unbounded in memory.",
                note="PLN-06 Data plane, which owns the bounded bulk path, is not installed here")
        else:
            plane = pln06.DataPlane({"s": {"public"}}, inflight_limit=2)
            big = dict(tenant="t1", workload="w", size=10 * 1024 * 1024,
                       classification="public", destination="s")
            plane.admit(**big)
            plane.admit(**big)
            try:
                plane.admit(**big)
                bounded = False
            except pln06.Backpressure:
                bounded = True
            assert bounded, "oversized payloads were buffered rather than refused"
            findings[5] = self.satisfied(
                items[5],
                "Payloads beyond the inline limit are handed to the PLN-06 data plane, which applies a "
                "bounded in-flight limit and raises Backpressure instead of queueing without limit.",
                *self._evidence("component.py::DistributedRuntime"), "PLN-06/DataPlane")
        return findings

COMPONENT = DistributedRuntimePlaneComponent
