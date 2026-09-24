"""INV-31 - Function execution architecture.

The function execution architecture is the request-scoped end of the spectrum: an invocation gets an instance, does one job, and the instance is either recycled within its tenant or destroyed. Everything hard about it is the reuse decision, so that is what this element owns.

The component answers all 100 requirements of the INV-31 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Maximum invocations concurrently sharing one instance.
CONCURRENCY_LIMIT = 4

#: Maximum instance age in logical ticks before eviction.
MAX_AGE = 300


class ConcurrencyExceeded(RuntimeError):
    """Raised when an instance is already at its concurrency bound."""


@dataclass
class Instance:
    """One function instance, bound to a tenant and a code version for its whole life."""

    name: str
    tenant: str
    version: str
    created_at: int
    in_flight: int = 0
    invocations: int = 0
    scratch: dict = field(default_factory=dict)

    def reusable_for(self, tenant: str, version: str, now: int) -> bool:
        return (self.tenant == tenant and self.version == version
                and now - self.created_at <= MAX_AGE)

    def enter(self) -> None:
        if self.in_flight >= CONCURRENCY_LIMIT:
            raise ConcurrencyExceeded(
                f"{self.name}: already at {CONCURRENCY_LIMIT} concurrent invocations")
        self.in_flight += 1

    def leave(self) -> None:
        self.in_flight = max(0, self.in_flight - 1)
        # Invocation-scoped state never survives the invocation that created it.
        self.scratch.clear()


@dataclass
class FunctionPool:
    """A pool of function instances with a strict reuse rule."""

    instances: list = field(default_factory=list)
    next_id: int = 0
    clears: int = 0

    def evict_aged(self, now: int) -> list:
        aged = [i for i in self.instances if now - i.created_at > MAX_AGE and i.in_flight == 0]
        for instance in aged:
            self.instances.remove(instance)
        return [i.name for i in aged]

    def invoke(self, *, tenant: str, version: str, now: int) -> dict:
        self.evict_aged(now)
        warm = next((i for i in self.instances
                     if i.reusable_for(tenant, version, now) and i.in_flight < CONCURRENCY_LIMIT),
                    None)
        cold = warm is None
        if cold:
            self.next_id += 1
            warm = Instance(f"fn-{self.next_id}", tenant, version, now)
            self.instances.append(warm)
        warm.enter()
        warm.scratch["request"] = f"{tenant}/{now}"
        warm.invocations += 1
        warm.leave()
        self.clears += 1
        return {"schema": "PK_INVOCATION/1", "instance": warm.name, "tenant": tenant,
                "version": version, "cold": cold,
                "invocations_on_instance": warm.invocations,
                "scratch_cleared": not warm.scratch}


class FunctionExecutionArchitectureComponent(Component):
    """Master-applied component for INV-31."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        pool = FunctionPool()
        first = pool.invoke(tenant="t1", version="v1", now=0)
        second = pool.invoke(tenant="t1", version="v1", now=1)
        assert first["cold"] and not second["cold"]
        assert second["instance"] == first["instance"]
        assert second["scratch_cleared"]
        findings[5] = self.satisfied(
            items[5],
            "The first invocation is cold, the second reuses the same instance warm, and invocation-scoped "
            "scratch is empty again afterwards.",
            *self._evidence("component.py::FunctionPool.invoke"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pool = FunctionPool()
        a = pool.invoke(tenant="t1", version="v1", now=0)
        b = pool.invoke(tenant="t2", version="v1", now=1)
        assert b["cold"] and b["instance"] != a["instance"]
        findings[5] = self.satisfied(
            items[5],
            "A second tenant never lands on the first tenant's warm instance: the reuse rule matches on "
            "tenant, so cross-tenant reuse costs a cold start rather than leaking memory.",
            *self._evidence("component.py::Instance.reusable_for"))
        c = pool.invoke(tenant="t1", version="v2", now=2)
        assert c["cold"] and c["instance"] != a["instance"]
        findings[4] = self.satisfied(
            items[4],
            "A new code version also forces a cold instance, so a warm pool cannot keep serving a "
            "superseded version after a deploy.",
            *self._evidence("component.py::Instance.reusable_for"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        instance = Instance("fn-1", "t1", "v1", 0)
        for _ in range(CONCURRENCY_LIMIT):
            instance.enter()
        try:
            instance.enter()
        except ConcurrencyExceeded:
            findings[5] = self.satisfied(
                items[5],
                f"Per-instance concurrency is bounded at {CONCURRENCY_LIMIT}; the {CONCURRENCY_LIMIT + 1}th "
                "invocation is refused rather than piled onto shared mutable state.",
                *self._evidence("component.py::Instance.enter"))
        pool = FunctionPool()
        pool.invoke(tenant="t1", version="v1", now=0)
        assert pool.evict_aged(MAX_AGE + 1) and not pool.instances
        aged = pool.invoke(tenant="t1", version="v1", now=MAX_AGE + 2)
        assert aged["cold"]
        findings[6] = self.satisfied(
            items[6],
            f"Instances past {MAX_AGE} ticks are evicted, so no instance accumulates state across an "
            "unbounded number of invocations.",
            *self._evidence("component.py::FunctionPool.evict_aged"))
        return findings

COMPONENT = FunctionExecutionArchitectureComponent
