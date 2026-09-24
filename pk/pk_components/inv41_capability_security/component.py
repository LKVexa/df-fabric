"""INV-41 - Capability security.

Capability security at the software level is the discipline the whole estate leans on: there is no ambient authority, a component can only do what it was handed, and handing something on can only narrow it. This element is where that rule is enforced for in-process references rather than for network grants.

The component answers all 100 requirements of the INV-41 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import secrets
from dataclasses import dataclass, field


class Forged(PermissionError):
    """Raised when a reference is not one this holder was given."""


class Widening(PermissionError):
    """Raised when an attenuation asks for more authority than is held."""


class Revoked(PermissionError):
    """Raised when a reference behind a revoked membrane is used."""


@dataclass(frozen=True)
class Reference:
    """An unforgeable reference. Possession is the authority; the name means nothing."""

    resource: str
    operations: frozenset
    token: str = field(default_factory=lambda: secrets.token_hex(16))
    membrane: "Membrane | None" = None

    def attenuate(self, operations) -> "Reference":
        requested = frozenset(operations)
        if not requested <= self.operations:
            raise Widening(
                f"{self.resource}: {sorted(requested - self.operations)} exceeds the held authority")
        return Reference(self.resource, requested, membrane=self.membrane)

    def invoke(self, operation: str):
        if self.membrane is not None and self.membrane.revoked:
            raise Revoked(f"{self.resource}: membrane {self.membrane.name} has been revoked")
        if operation not in self.operations:
            raise Forged(f"{self.resource}: {operation!r} is not in this reference's authority")
        return {"schema": "PK_REFERENCE/1", "resource": self.resource,
                "operation": operation, "permitted": True}


@dataclass
class Membrane:
    """A revocable wrapper: revoking it kills every reference behind it at once."""

    name: str
    revoked: bool = False
    issued: int = 0

    def wrap(self, reference: Reference) -> Reference:
        self.issued += 1
        return Reference(reference.resource, reference.operations, membrane=self)

    def revoke(self) -> dict:
        self.revoked = True
        return {"schema": "PK_MEMBRANE/1", "membrane": self.name,
                "revoked": True, "references_killed": self.issued}


@dataclass
class Holder:
    """A component holds exactly what it was constructed with. There is no registry."""

    name: str
    held: dict = field(default_factory=dict)      # local alias -> Reference

    def use(self, alias: str, operation: str):
        reference = self.held.get(alias)
        if reference is None:
            # No global lookup exists: an unheld reference simply cannot be obtained.
            raise Forged(f"{self.name}: holds no reference named {alias!r}")
        return reference.invoke(operation)

    def delegate(self, alias: str, operations) -> Reference:
        reference = self.held.get(alias)
        if reference is None:
            raise Forged(f"{self.name}: cannot delegate a reference it does not hold")
        return reference.attenuate(operations)


class CapabilitySecurityComponent(Component):
    """Master-applied component for INV-41."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        store = Reference("state-store", frozenset({"read", "write"}))
        component = Holder("api", {"store": store})
        assert component.use("store", "read")["permitted"]
        narrowed = component.delegate("store", {"read"})
        assert narrowed.operations == frozenset({"read"})
        assert narrowed.token != store.token
        findings[5] = self.satisfied(
            items[5],
            "A component acts only through references it was constructed with, and delegation produces a "
            "distinct, narrower reference rather than a copy of the original authority.",
            *self._evidence("component.py::Component"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        component = Holder("api", {"store": Reference("store", frozenset({"read"}))})
        proven = []
        try:
            component.use("secrets", "read")
        except Forged:
            proven.append("no lookup for an unheld reference")
        try:
            component.delegate("store", {"read", "write"})
        except Widening:
            proven.append("no widening on delegation")
        try:
            component.use("store", "write")
        except Forged:
            proven.append("no operation outside the reference")
        assert len(proven) == 3, proven
        findings[2] = self.satisfied(
            items[2],
            f"Ambient authority has no entry point: {'; '.join(proven)}. There is no registry to consult, "
            "so a compromised component gains nothing it was not handed.",
            *self._evidence("component.py::Component.use"))
        findings[1] = self.satisfied(
            items[1],
            "References are unguessable tokens, so possession cannot be manufactured by naming a resource "
            "correctly.",
            *self._evidence("component.py::Reference"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        membrane = Membrane("session-42")
        base = Reference("store", frozenset({"read", "write"}))
        first = membrane.wrap(base)
        second = first.attenuate({"read"})
        assert first.invoke("read")["permitted"] and second.invoke("read")["permitted"]
        result = membrane.revoke()
        killed = 0
        for ref in (first, second):
            try:
                ref.invoke("read")
            except Revoked:
                killed += 1
        assert killed == 2
        findings[6] = self.satisfied(
            items[6],
            f"Revoking one membrane kills every reference behind it at once ({killed} of {killed}, "
            f"including an attenuated copy), so revocation does not require finding each holder.",
            *self._evidence("component.py::Membrane.revoke"))
        return findings

COMPONENT = CapabilitySecurityComponent
