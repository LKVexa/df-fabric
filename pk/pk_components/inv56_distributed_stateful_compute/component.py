"""INV-56 - Distributed stateful compute.

Distributed stateful compute is the virtual-actor model: an actor is addressed by id, activated on some host when first called, and processes one message at a time. The guarantees that make it useful are single activation -- never two live copies of the same actor -- and turn-based execution, so actor code needs no locks.

The component answers all 100 requirements of the INV-56 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class TurnViolation(RuntimeError):
    pass


@dataclass
class Actor:
    actor_id: str
    state: dict
    busy: bool = False

    def turn(self, fn):
        if self.busy:
            raise TurnViolation(f"{self.actor_id} already in a turn")
        self.busy = True
        try:
            return fn(self.state)
        finally:
            self.busy = False


@dataclass
class ActorSystem:
    hosts: list
    placement: dict = field(default_factory=dict)       # actor -> host
    live: dict = field(default_factory=dict)            # (host, actor) -> Actor
    store: dict = field(default_factory=dict)
    reactivations: int = 0

    def _activate(self, actor_id: str) -> Actor:
        host = self.placement.get(actor_id)
        if host is None or host not in self.hosts:
            if host is not None:
                self.reactivations += 1
            host = self.hosts[sum(map(ord, actor_id)) % len(self.hosts)]
            self.placement[actor_id] = host
        key = (host, actor_id)
        if key not in self.live:
            self.live[key] = Actor(actor_id, dict(self.store.get(actor_id, {})))
        return self.live[key]

    def call(self, actor_id: str, fn):
        actor = self._activate(actor_id)
        result = actor.turn(fn)
        self.store[actor_id] = dict(actor.state)     # persist after every turn
        return result

    def activations(self, actor_id: str) -> int:
        return sum(1 for (_, a) in self.live if a == actor_id)

    def lose_host(self, host: str) -> None:
        self.hosts.remove(host)
        self.live = {k: v for k, v in self.live.items() if k[0] != host}


class DistributedStatefulComputeComponent(Component):
    """Master-applied component for INV-56."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        sys_ = ActorSystem(["h1", "h2", "h3"])
        for _ in range(50):
            sys_.call("cart-7", lambda s: s.__setitem__("n", s.get("n", 0) + 1))
        assert sys_.activations("cart-7") == 1
        findings[0] = self.satisfied(
            items[0],
            "Fifty calls to one actor id all reached a single activation on one host; the placement "
            "table, not the caller, decides where an actor lives.",
            *self._evidence("component.py::ActorSystem._activate"))

        a = Actor("x", {})
        overlapped = False
        def reenter(state):
            nonlocal overlapped
            try:
                a.turn(lambda s: None)
            except TurnViolation:
                overlapped = True
        a.turn(reenter)
        assert overlapped
        findings[1] = self.satisfied(
            items[1],
            "Turns do not overlap: a second turn attempted while one is running is refused, so actor "
            "code runs without locks.",
            *self._evidence("component.py::Actor.turn"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = ActorSystem(["h1", "h2"])
        s.call("acct-1", lambda st: st.__setitem__("balance", 100))
        home = s.placement["acct-1"]
        s.lose_host(home)
        bal = s.call("acct-1", lambda st: st.get("balance"))
        assert bal == 100 and s.placement["acct-1"] != home and s.reactivations == 1
        assert s.activations("acct-1") == 1
        findings[0] = self.satisfied(
            items[0],
            "When an actor's host is lost the actor reactivates on a surviving host with its persisted "
            "state (balance 100 intact) and still exactly one activation.",
            *self._evidence("component.py::ActorSystem.lose_host", "component.py::ActorSystem.call"))
        return findings

COMPONENT = DistributedStatefulComputeComponent
