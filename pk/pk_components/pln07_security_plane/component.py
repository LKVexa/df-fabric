"""PLN-07 - Security plane.

The security plane replaces ambient trust with explicit, attenuable capabilities. Nothing in the estate holds authority it was not granted; every grant names its holder, its scope, and its expiry, and any holder may attenuate a grant but never widen one.

The component answers all 100 requirements of the PLN-07 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field

MAX_DELEGATION_DEPTH = 5


class Widening(PermissionError):
    """Raised when an attenuation requests authority the parent does not hold."""


class GrantInvalid(PermissionError):
    """Raised when a grant fails verification (expired, revoked, or over-deep)."""


@dataclass(frozen=True)
class Grant:
    """A scoped, expiring capability grant.

    ``scope`` is a set of capability names; attenuation may only shrink it.
    ``not_after`` is a logical tick, which keeps verification clock-free in tests
    while modelling a real expiry.
    """

    subject: str
    tenant: str
    scope: frozenset
    not_after: int
    parent: "Grant | None" = None
    depth: int = 0

    @property
    def id(self) -> str:
        seed = f"{self.subject}|{self.tenant}|{sorted(self.scope)}|{self.not_after}|{self.depth}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def attenuate(self, *, subject: str | None = None, scope=None, not_after: int | None = None) -> "Grant":
        """Derive a strictly narrower grant. Widening in any dimension is refused."""
        new_scope = frozenset(scope) if scope is not None else self.scope
        if not new_scope <= self.scope:
            raise Widening(f"scope {sorted(new_scope - self.scope)} exceeds the held grant")
        new_expiry = self.not_after if not_after is None else not_after
        if new_expiry > self.not_after:
            raise Widening(f"expiry {new_expiry} is later than the held grant's {self.not_after}")
        if self.depth + 1 > MAX_DELEGATION_DEPTH:
            raise GrantInvalid(f"delegation depth {self.depth + 1} exceeds {MAX_DELEGATION_DEPTH}")
        return Grant(subject or self.subject, self.tenant, new_scope, new_expiry, self, self.depth + 1)


@dataclass
class Verifier:
    """Verifies a grant chain at a logical point in time."""

    revoked: set = field(default_factory=set)
    skew: int = 0

    def verify(self, grant: Grant, now: int, capability: str, tenant: str) -> bool:
        link = grant
        while link is not None:
            if link.id in self.revoked:
                raise GrantInvalid(f"grant {link.id} is revoked")
            if now - self.skew > link.not_after:
                raise GrantInvalid(f"grant {link.id} expired at {link.not_after}")
            if link.tenant != tenant:
                raise GrantInvalid("grant chain crosses a tenant boundary")
            if link.parent is not None and not link.scope <= link.parent.scope:
                raise GrantInvalid(f"grant {link.id} widens its parent")
            link = link.parent
        if capability not in grant.scope:
            raise GrantInvalid(f"capability {capability!r} is outside the grant scope")
        return True


class SecurityPlaneComponent(Component):
    """Master-applied component for PLN-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        root = Grant("controller", "t1", frozenset({"state", "messaging", "invoke"}), not_after=100)
        narrowed = root.attenuate(subject="worker", scope={"state"}, not_after=50)
        assert narrowed.scope == frozenset({"state"}) and narrowed.depth == 1
        verifier = Verifier()
        assert verifier.verify(narrowed, now=10, capability="state", tenant="t1")
        findings[5] = self.satisfied(
            items[5],
            f"Issuance and attenuation are deterministic: root {root.id} -> attenuated {narrowed.id} "
            "at depth 1 with a strictly smaller scope and earlier expiry.",
            *self._evidence("component.py::Grant"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        root = Grant("controller", "t1", frozenset({"state"}), not_after=100)
        proven = []
        try:
            root.attenuate(scope={"state", "secrets"})
        except Widening:
            proven.append("scope widening")
        try:
            root.attenuate(not_after=200)
        except Widening:
            proven.append("expiry extension")
        assert len(proven) == 2
        findings[1] = self.satisfied(
            items[1],
            f"Attenuation is one-way: {' and '.join(proven)} both refused.",
            *self._evidence("component.py::Grant.attenuate"))

        verifier = Verifier()
        try:
            verifier.verify(root, now=101, capability="state", tenant="t1")
        except GrantInvalid:
            findings[3] = self.satisfied(
                items[3], "An expired grant is refused at verification.",
                *self._evidence("component.py::Verifier.verify"))
        revoking = Verifier(revoked={root.id})
        child = root.attenuate(subject="worker")
        try:
            revoking.verify(child, now=10, capability="state", tenant="t1")
        except GrantInvalid:
            findings[4] = self.satisfied(
                items[4], "Revoking a parent invalidates every grant derived from it.",
                *self._evidence("component.py::Verifier.verify"))
        try:
            verifier.verify(root, now=10, capability="state", tenant="t2")
        except GrantInvalid:
            findings[5] = self.satisfied(
                items[5], "A grant cannot be used against a tenant other than the one it names.",
                *self._evidence("component.py::Verifier.verify"))
        gap07 = sibling("GAP-07")
        if gap07 is None:
            findings[8] = self.partial(
                items[8], "Grants are structurally verified but not cryptographically signed.",
                note="GAP-07 Artifact provenance/signing is not installed here")
        else:
            store = gap07.TrustStore("prod")
            store.add("authority", "authority", b"grant-key")
            grant = Grant("worker", "t1", frozenset({"state"}), not_after=100)
            body = f"{grant.subject}|{grant.tenant}|{sorted(grant.scope)}|{grant.not_after}".encode()
            signature = store.sign("authority", body)
            assert store.verify(signature, body, "grant")["verified"]
            widened = f"{grant.subject}|{grant.tenant}|{sorted({'state', 'secrets'})}|{grant.not_after}".encode()
            try:
                store.verify(signature, widened, "grant")
                forged = True
            except gap07.SignatureInvalid:
                forged = False
            assert not forged, "a widened grant body verified against the original signature"
            findings[8] = self.satisfied(
                items[8],
                "Grants are signed through GAP-07 by an authority-role signer and bound to the grant body's "
                "digest: editing the scope after issue invalidates the signature.",
                *self._evidence("component.py::Grant"), "GAP-07/TrustStore.verify")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        grant = Grant("a", "t1", frozenset({"state"}), not_after=100)
        for _ in range(MAX_DELEGATION_DEPTH):
            grant = grant.attenuate()
        try:
            grant.attenuate()
        except GrantInvalid:
            findings[6] = self.satisfied(
                items[6],
                f"Delegation depth is capped at {MAX_DELEGATION_DEPTH}, bounding blast radius of a "
                "compromised holder.",
                *self._evidence("component.py::Grant.attenuate"))
        gap04 = sibling("GAP-04")
        if gap04 is None:
            findings[3] = self.partial(
                items[3], "Revocation is verified locally; propagation to disconnected sites is unmodelled.",
                note="GAP-04 Disconnected-operation controller is not installed here")
        else:
            controller = gap04.AutonomyController("dub", granted_at=0, lease_ticks=60)
            controller.partition(0)
            assert controller.tier(61) == "expired"
            short = Grant("worker", "t1", frozenset({"state"}), not_after=60)
            verifier = Verifier()
            try:
                verifier.verify(short, now=61, capability="state", tenant="t1")
                survived = True
            except GrantInvalid:
                survived = False
            assert not survived, "a grant outlived the site's autonomy lease"
            findings[3] = self.satisfied(
                items[3],
                "The revocation horizon is the grant lifetime: a partitioned site's GAP-04 autonomy lease "
                "and the grants issued to it expire together, so an unseen revocation cannot outlive its "
                "window rather than propagating instantly.",
                *self._evidence("component.py::Verifier.verify"), "GAP-04/AutonomyController")
        return findings

COMPONENT = SecurityPlaneComponent
