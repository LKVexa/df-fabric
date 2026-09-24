"""INV-65 - Capability providers.

Capability providers are the long-lived processes that give components access to the outside world -- a key-value store, an HTTP server, a message broker -- behind a contract id. One provider serves many links, so the rule that matters is isolation between them: each link has its own configuration and credentials, and one component cannot see or use another's.

The component answers all 100 requirements of the INV-65 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import copy
from dataclasses import dataclass, field


class NoLink(PermissionError):
    pass


@dataclass
class Provider:
    contract: str
    links: dict = field(default_factory=dict)      # component -> config
    backend_ok: bool = True
    restarts: int = 0
    _snapshot: dict = field(default_factory=dict)

    def link(self, component: str, config: dict) -> None:
        self.links[component] = copy.deepcopy(config)

    def call(self, component: str, op: str):
        cfg = self.links.get(component)
        if cfg is None:
            raise NoLink(f"{component} has no link to {self.contract}")
        return {"op": op, "bucket": cfg["bucket"], "as": cfg["user"]}

    def health(self) -> str:
        return "healthy" if self.backend_ok and self.links is not None else "unhealthy"

    def checkpoint(self) -> None:
        self._snapshot = copy.deepcopy(self.links)

    def restart(self) -> int:
        self.links = {}
        self.restarts += 1
        self.links = copy.deepcopy(self._snapshot)
        return len(self.links)


class CapabilityProvidersComponent(Component):
    """Master-applied component for INV-65."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "orders", "user": "orders-rw"})
        p.link("reports", {"bucket": "reports", "user": "reports-ro"})
        o, r = p.call("orders", "get"), p.call("reports", "get")
        nolink = False
        try:
            p.call("marketing", "get")
        except NoLink:
            nolink = True
        assert o["as"] == "orders-rw" and r["as"] == "reports-ro" and nolink
        findings[0] = self.satisfied(
            items[0],
            "One provider serves two components, each with its own bucket and credentials; neither call "
            "sees the other's configuration, and a component with no link is refused.",
            *self._evidence("component.py::Provider.call"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Provider("wasi:keyvalue")
        p.link("a", {"bucket": "a", "user": "u"})
        p.link("b", {"bucket": "b", "user": "u"})
        p.checkpoint()
        restored = p.restart()
        assert restored == 2 and p.call("b", "get")["bucket"] == "b"
        p.backend_ok = False
        assert p.health() == "unhealthy"
        findings[0] = self.satisfied(
            items[0],
            f"A restarted provider restores all {restored} links from its checkpoint so components keep "
            "working, and a failed backend is reported unhealthy rather than masked.",
            *self._evidence("component.py::Provider.restart", "component.py::Provider.health"))
        return findings

COMPONENT = CapabilityProvidersComponent
