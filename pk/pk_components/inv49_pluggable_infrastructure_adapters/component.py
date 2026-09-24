"""INV-49 - Pluggable infrastructure adapters.

Pluggable infrastructure adapters are how a new database or broker joins the runtime without changing an application. The value is only real if the plug is checked: an adapter declares the contract and optional features it implements, and the loader verifies that declaration against the adapter itself before admitting it -- a claimed feature that is not there is refused at load, not discovered in production.

The component answers all 100 requirements of the INV-49 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

CONTRACTS = {
    "state/v1": {"required": ("get", "set", "delete"),
                 "features": {"etag": ("get_with_etag",), "transactional": ("transact",)}},
    "pubsub/v1": {"required": ("publish", "subscribe"),
                  "features": {"ordering": ("publish_ordered",)}},
}


class AdmissionRefused(ValueError):
    """Raised when an adapter's declaration does not match what it implements."""


@dataclass
class Loader:
    admitted: dict = field(default_factory=dict)
    refusals: list = field(default_factory=list)
    faults: int = 0

    def admit(self, name: str, adapter, contract: str, version: str, features=()):
        spec = CONTRACTS.get(contract)
        reasons = []
        if spec is None:
            reasons.append(f"unknown contract {contract}")
        else:
            reasons += [f"missing {m}" for m in spec["required"] if not callable(getattr(adapter, m, None))]
            for f in features:
                needed = spec["features"].get(f)
                if needed is None:
                    reasons.append(f"feature {f} not defined by {contract}")
                else:
                    reasons += [f"feature {f} claims {m}, absent" for m in needed
                                if not callable(getattr(adapter, m, None))]
        if not version or version in ("latest", "*"):
            reasons.append("version not pinned")
        if reasons:
            self.refusals.append((name, reasons))
            raise AdmissionRefused(f"{name}: {reasons}")
        self.admitted[name] = {"adapter": adapter, "contract": contract, "version": version,
                               "features": frozenset(features)}

    def call(self, name: str, method: str, *args):
        try:
            return ("ok", getattr(self.admitted[name]["adapter"], method)(*args))
        except Exception as exc:  # contained to this component
            self.faults += 1
            return ("fault", f"{name}.{method}: {type(exc).__name__}")


class GoodStore:
    def __init__(self): self.d = {}
    def get(self, k): return self.d.get(k)
    def set(self, k, v): self.d[k] = v
    def delete(self, k): self.d.pop(k, None)
    def get_with_etag(self, k): return self.d.get(k), hash(self.d.get(k))


class Boasting(GoodStore):
    """Claims to be transactional but has no transact method."""


class PluggableInfrastructureAdaptersComponent(Component):
    """Master-applied component for INV-49."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        ld = Loader()
        ld.admit("good", GoodStore(), "state/v1", "1.2.0", features=["etag"])
        refused = False
        try:
            ld.admit("liar", Boasting(), "state/v1", "1.2.0", features=["transactional"])
        except AdmissionRefused:
            refused = True
        unpinned = False
        try:
            ld.admit("floating", GoodStore(), "state/v1", "latest")
        except AdmissionRefused:
            unpinned = True
        assert refused and unpinned and list(ld.admitted) == ["good"]
        findings[0] = self.satisfied(
            items[0],
            "Declarations are verified against the adapter itself: a store claiming transactions with no "
            "transact method is refused, as is one pinned to 'latest', and only the honest adapter is admitted.",
            *self._evidence("component.py::Loader.admit", "component.py::CONTRACTS"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        class Flaky(GoodStore):
            def get(self, k): raise ConnectionError("backend down")
        ld = Loader()
        ld.admit("flaky", Flaky(), "state/v1", "1.0.0")
        ld.admit("steady", GoodStore(), "state/v1", "1.0.0")
        bad = ld.call("flaky", "get", "k")
        ld.call("steady", "set", "k", 1)
        assert bad[0] == "fault" and ld.call("steady", "get", "k") == ("ok", 1)
        findings[0] = self.satisfied(
            items[0],
            "An adapter's exception is converted into a fault result for its own component; the "
            "neighbouring adapter keeps serving, so one broken backend does not take the runtime down.",
            *self._evidence("component.py::Loader.call"))
        return findings

COMPONENT = PluggableInfrastructureAdaptersComponent
