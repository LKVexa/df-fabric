"""INV-48 - Service communication APIs.

Service communication APIs are how one application calls another by name: resolve the name, carry the caller's identity, apply a timeout, and retry only when the operation is safe to repeat. The discipline is in the retry -- a non-idempotent call retried after a timeout can charge a card twice, so retries are keyed and deduplicated at the callee.

The component answers all 100 requirements of the INV-48 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class Unresolvable(KeyError):
    """Raised when a logical service name has no endpoint."""


class RetriesExhausted(RuntimeError):
    """Raised when every permitted attempt has failed."""


class Transient(RuntimeError):
    """A failure the policy may retry."""


@dataclass
class Callee:
    effects: int = 0
    seen: dict = field(default_factory=dict)
    fail_first: int = 0
    duplicates: int = 0
    identities: list = field(default_factory=list)

    def handle(self, identity: str, key, payload):
        self.identities.append(identity)
        if key is not None and key in self.seen:
            self.duplicates += 1
            return self.seen[key]
        if self.fail_first > 0:
            # The effect happens, but the response is lost -- the dangerous case.
            self.fail_first -= 1
            self.effects += 1
            if key is not None:
                self.seen[key] = f"done:{payload}"
            raise Transient("response lost")
        self.effects += 1
        result = f"done:{payload}"
        if key is not None:
            self.seen[key] = result
        return result


@dataclass
class Invoker:
    registry: dict
    max_attempts: int = 3
    backoff_ms: tuple = (10, 40, 160)
    retries: int = 0
    waited_ms: int = 0

    def call(self, service: str, identity: str, payload, key=None):
        if service not in self.registry:
            raise Unresolvable(service)
        callee = self.registry[service]
        attempts = self.max_attempts if key is not None else 1
        for n in range(attempts):
            try:
                return callee.handle(identity, key, payload)
            except Transient:
                if n + 1 == attempts:
                    raise RetriesExhausted(f"{service}: {attempts} attempt(s)")
                self.retries += 1
                self.waited_ms += self.backoff_ms[min(n, len(self.backoff_ms) - 1)]


class ServiceCommunicationApisComponent(Component):
    """Master-applied component for INV-48."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        callee = Callee(fail_first=1)
        inv = Invoker({"payments": callee})
        assert inv.call("payments", "spiffe://shop", "charge-10", key="k-1") == "done:charge-10"
        assert callee.effects == 1 and callee.duplicates == 1 and inv.retries == 1

        risky = Callee(fail_first=1)
        inv2 = Invoker({"payments": risky})
        unkeyed = False
        try:
            inv2.call("payments", "spiffe://shop", "charge-10")
        except RetriesExhausted:
            unkeyed = True
        assert unkeyed and risky.effects == 1
        findings[0] = self.satisfied(
            items[0],
            "A keyed call whose response was lost is retried and the callee returns the recorded result "
            "instead of charging again (1 effect, 1 duplicate suppressed); an unkeyed call is never "
            "retried, so a lost response cannot become a second side effect.",
            *self._evidence("component.py::Invoker.call", "component.py::Callee.handle"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        callee = Callee(fail_first=1)
        Invoker({"svc": callee}).call("svc", "spiffe://caller", "x", key="k")
        assert set(callee.identities) == {"spiffe://caller"} and len(callee.identities) == 2
        findings[2] = self.satisfied(
            items[2],
            "The caller's identity reaches the callee on the first attempt and on the retry, so an "
            "authorization decision downstream never sees an anonymous call.",
            *self._evidence("component.py::Invoker.call"))
        return findings

COMPONENT = ServiceCommunicationApisComponent
