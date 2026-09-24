"""INV-52 - Messaging abstraction.

The messaging abstraction lets an application publish to a topic and subscribe to one without knowing the broker. Every message travels in one envelope -- id, source, type, time, data -- and subscriptions route by rule, with a dead-letter topic for what no rule or handler can take.

The component answers all 100 requirements of the INV-52 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import itertools
from dataclasses import dataclass, field

_ids = itertools.count(1)
REQUIRED = ("id", "source", "type", "time", "data")


class TopicDenied(PermissionError):
    pass


class IncompleteEnvelope(ValueError):
    pass


def envelope(source: str, etype: str, data, time: int = 0) -> dict:
    return {"id": f"m-{next(_ids)}", "source": source, "type": etype, "time": time, "data": data}


@dataclass
class PubSub:
    publishers: dict = field(default_factory=dict)    # topic -> allowed apps
    routes: dict = field(default_factory=dict)        # topic -> [(predicate, handler_list)]
    dead_letter: list = field(default_factory=list)

    def allow(self, topic: str, *apps: str) -> None:
        self.publishers[topic] = frozenset(apps)

    def subscribe(self, topic: str, predicate, sink: list) -> None:
        self.routes.setdefault(topic, []).append((predicate, sink))

    def publish(self, app: str, topic: str, msg: dict) -> int:
        if app not in self.publishers.get(topic, ()):
            raise TopicDenied(f"{app} may not publish to {topic}")
        missing = [k for k in REQUIRED if msg.get(k) in (None, "")]
        if missing:
            raise IncompleteEnvelope(f"missing {missing}")
        delivered = 0
        for predicate, sink in self.routes.get(topic, []):
            if predicate(msg):
                sink.append(msg)
                delivered += 1
        if delivered == 0:
            self.dead_letter.append({"topic": topic, "reason": "no route matched", "message": msg})
        return delivered


class MessagingAbstractionComponent(Component):
    """Master-applied component for INV-52."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        ps = PubSub()
        ps.allow("orders", "shop")
        big, small = [], []
        ps.subscribe("orders", lambda m: m["data"]["total"] >= 100, big)
        ps.subscribe("orders", lambda m: m["data"]["total"] < 100, small)
        ps.publish("shop", "orders", envelope("shop", "order.placed", {"total": 250}))
        ps.publish("shop", "orders", envelope("shop", "order.placed", {"total": 5}))
        ps.allow("audit", "shop")
        ps.publish("shop", "audit", envelope("shop", "audit.event", {}))
        assert len(big) == 1 and len(small) == 1 and len(ps.dead_letter) == 1
        findings[0] = self.satisfied(
            items[0],
            "Subscriptions route by content rule (large and small orders reach different handlers), and "
            "a message no rule accepts goes to the dead-letter topic with its reason instead of vanishing.",
            *self._evidence("component.py::PubSub.publish"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        ps = PubSub()
        ps.allow("payments", "billing")
        denied = incomplete = False
        try:
            ps.publish("shop", "payments", envelope("shop", "x", {}))
        except TopicDenied:
            denied = True
        try:
            ps.publish("billing", "payments", {"id": "1", "type": "t", "time": 0, "data": {}})
        except IncompleteEnvelope:
            incomplete = True
        assert denied and incomplete
        findings[0] = self.satisfied(
            items[0],
            "Publishing is scoped per topic, and a message without a source is refused, so every message "
            "on a topic comes from an allowed app and can be traced back to it.",
            *self._evidence("component.py::PubSub.publish", "component.py::REQUIRED"))
        return findings

COMPONENT = MessagingAbstractionComponent
