"""INV-53 - Message reliability.

Message reliability turns 'published' into 'processed'. Delivery is at-least-once: a message stays owned by the broker until the consumer acknowledges it, reappears if the consumer dies holding it, and after a bounded number of attempts is parked in a dead-letter queue instead of looping forever. Because redelivery happens, consumers deduplicate by message id.

The component answers all 100 requirements of the INV-53 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


@dataclass
class ReliableQueue:
    visibility: int = 10
    max_attempts: int = 3
    ready: list = field(default_factory=list)
    in_flight: dict = field(default_factory=dict)   # id -> (msg, deadline)
    attempts: dict = field(default_factory=dict)
    dlq: list = field(default_factory=list)
    redeliveries: int = 0

    def put(self, msg: dict) -> None:
        self.ready.append(msg)

    def receive(self, now: int):
        self._expire(now)
        while self.ready:
            msg = self.ready.pop(0)
            n = self.attempts.get(msg["id"], 0) + 1
            if n > self.max_attempts:
                self.dlq.append({"message": msg, "attempts": n - 1})
                continue
            self.attempts[msg["id"]] = n
            self.in_flight[msg["id"]] = (msg, now + self.visibility)
            return msg
        return None

    def ack(self, msg_id: str) -> bool:
        return self.in_flight.pop(msg_id, None) is not None

    def _expire(self, now: int) -> None:
        for mid, (msg, deadline) in list(self.in_flight.items()):
            if now >= deadline:
                del self.in_flight[mid]
                self.ready.append(msg)
                self.redeliveries += 1


@dataclass
class IdempotentConsumer:
    done: set = field(default_factory=set)
    effects: int = 0
    skipped: int = 0

    def handle(self, msg: dict) -> None:
        if msg["id"] in self.done:
            self.skipped += 1
            return
        self.effects += 1
        self.done.add(msg["id"])


class MessageReliabilityComponent(Component):
    """Master-applied component for INV-53."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        q = ReliableQueue(visibility=5)
        q.put({"id": "m1", "data": 1})
        m = q.receive(now=0)            # consumer takes it, then crashes without ack
        assert q.receive(now=1) is None
        again = q.receive(now=6)
        assert again["id"] == "m1" and q.redeliveries == 1 and q.ack("m1")
        findings[0] = self.satisfied(
            items[0],
            "A message taken by a consumer that crashes before acknowledging is invisible during its "
            "visibility window and redelivered after it, so a consumer failure cannot lose it.",
            *self._evidence("component.py::ReliableQueue.receive", "component.py::ReliableQueue._expire"))

        p = ReliableQueue(visibility=1, max_attempts=3)
        p.put({"id": "poison"})
        t = 0
        while p.receive(now=t) is not None:
            t += 1
        assert len(p.dlq) == 1 and p.dlq[0]["attempts"] == 3
        findings[1] = self.satisfied(
            items[1],
            f"A message that fails every time is delivered exactly {p.max_attempts} times and then parked "
            "in the dead-letter queue with its attempt count, instead of looping forever.",
            *self._evidence("component.py::ReliableQueue.receive"))
        return findings

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = IdempotentConsumer()
        msg = {"id": "m9"}
        c.handle(msg)
        c.handle(msg)
        assert c.effects == 1 and c.skipped == 1
        findings[0] = self.satisfied(
            items[0],
            "At-least-once delivery is paired with consumer deduplication by message id: a redelivered "
            "message is recognised and produces no second effect.",
            *self._evidence("component.py::IdempotentConsumer"))
        return findings

COMPONENT = MessageReliabilityComponent
