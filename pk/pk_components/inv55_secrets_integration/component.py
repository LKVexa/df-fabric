"""INV-55 - Secrets integration.

Secrets integration lets an application reference a secret by name and get its value at run time without the value ever sitting in configuration, logs or the application's image. Access is scoped per application and per secret, values arrive with a version and a lease, and rotation is a new version rather than an overwrite.

The component answers all 100 requirements of the INV-55 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class SecretDenied(PermissionError):
    pass


class LeaseExpired(PermissionError):
    pass


class Secret(str):
    """A value that refuses to print itself."""

    def __repr__(self):
        return "Secret(***)"

    __str__ = __repr__

    def reveal(self) -> str:
        return str.__str__(self)


@dataclass
class SecretBroker:
    lease_ttl: int = 300
    versions: dict = field(default_factory=dict)     # name -> [values]
    scopes: dict = field(default_factory=dict)       # name -> apps
    log: list = field(default_factory=list)

    def put(self, name: str, value: str, apps) -> int:
        self.versions.setdefault(name, []).append(value)
        self.scopes[name] = frozenset(apps)
        return len(self.versions[name])

    def resolve(self, app: str, name: str, now: int):
        if app not in self.scopes.get(name, ()):
            self.log.append(f"deny {app} -> {name}")
            raise SecretDenied(f"{app} may not resolve {name}")
        version = len(self.versions[name])
        value = Secret(self.versions[name][-1])
        self.log.append(f"grant {app} -> {name} v{version} value={value}")
        return {"value": value, "version": version, "expires": now + self.lease_ttl}

    @staticmethod
    def use(lease: dict, now: int) -> str:
        if now >= lease["expires"]:
            raise LeaseExpired("lease ended; resolve again")
        return lease["value"].reveal()


class SecretsIntegrationComponent(Component):
    """Master-applied component for INV-55."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        b = SecretBroker(lease_ttl=60)
        b.put("db-password", "hunter2-prod", apps=["orders"])
        lease = b.resolve("orders", "db-password", now=0)
        denied = False
        try:
            b.resolve("marketing", "db-password", now=0)
        except SecretDenied:
            denied = True
        text = " ".join(b.log) + repr(lease) + f"{lease['value']}"
        assert denied and "hunter2" not in text and b.use(lease, now=10) == "hunter2-prod"
        findings[0] = self.satisfied(
            items[0],
            "A secret resolves only for the applications in its scope, and its value redacts itself in "
            "logs, reprs and f-strings -- the audit trail records every grant and denial without "
            "containing the value, which is revealed only by an explicit call.",
            *self._evidence("component.py::Secret", "component.py::SecretBroker.resolve"))

        expired = False
        try:
            b.use(lease, now=61)
        except LeaseExpired:
            expired = True
        assert expired
        findings[1] = self.satisfied(
            items[1],
            "Access is leased: the same value stops working at lease end, so a copied secret is useful "
            "only for its TTL.",
            *self._evidence("component.py::SecretBroker.use"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        b = SecretBroker()
        b.put("api-key", "v1-key", ["svc"])
        old = b.resolve("svc", "api-key", now=0)
        b.put("api-key", "v2-key", ["svc"])
        new = b.resolve("svc", "api-key", now=1)
        assert old["version"] == 1 and new["version"] == 2 and b.use(old, 2) == "v1-key"
        findings[0] = self.satisfied(
            items[0],
            "Rotation adds a version rather than overwriting: running holders keep a working v1 until "
            "their lease ends while new resolutions get v2, so rotation never breaks a live app.",
            *self._evidence("component.py::SecretBroker.put"))
        return findings

COMPONENT = SecretsIntegrationComponent
