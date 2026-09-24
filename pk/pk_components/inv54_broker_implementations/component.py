"""INV-54 - Broker implementations.

Broker implementations are the concrete engines behind the messaging contract. Two ship here: a fan-out broker that copies each message to every subscriber, and a partitioned log that keeps per-key order and lets consumers replay from an offset. They make opposite trade-offs, and the contract is only portable if both pass the same checks.

The component answers all 100 requirements of the INV-54 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import zlib
from dataclasses import dataclass, field


@dataclass
class FanoutBroker:
    subscribers: dict = field(default_factory=dict)

    def subscribe(self, name: str) -> list:
        return self.subscribers.setdefault(name, [])

    def publish(self, msg) -> int:
        for inbox in self.subscribers.values():
            inbox.append(msg)
        return len(self.subscribers)


@dataclass
class PartitionedLog:
    partitions: int = 4
    logs: list = field(default_factory=list)
    offsets: dict = field(default_factory=dict)      # (consumer, partition) -> offset

    def __post_init__(self):
        self.logs = [[] for _ in range(self.partitions)]

    def partition_for(self, key: str) -> int:
        return zlib.crc32(key.encode()) % self.partitions

    def append(self, key: str, msg) -> tuple:
        p = self.partition_for(key)
        self.logs[p].append((key, msg))
        return p, len(self.logs[p]) - 1

    def poll(self, consumer: str, partition: int, limit: int = 100) -> list:
        off = self.offsets.get((consumer, partition), 0)
        batch = self.logs[partition][off:off + limit]
        self.offsets[(consumer, partition)] = off + len(batch)
        return batch

    def seek(self, consumer: str, partition: int, offset: int) -> None:
        if not 0 <= offset <= len(self.logs[partition]):
            raise IndexError(f"offset {offset} out of range")
        self.offsets[(consumer, partition)] = offset


class BrokerImplementationsComponent(Component):
    """Master-applied component for INV-54."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        log = PartitionedLog()
        for i in range(20):
            for acct in ("acct-a", "acct-b", "acct-c"):
                log.append(acct, (acct, i))
        for acct in ("acct-a", "acct-b", "acct-c"):
            p = log.partition_for(acct)
            seq = [m[1] for k, m in log.poll("reader", p, 10_000) if k == acct]
            log.seek("reader", p, 0)
            assert seq == list(range(20))
        findings[0] = self.satisfied(
            items[0],
            "Messages for each key land in one partition and are read back in publish order (20 per "
            "account across 3 interleaved accounts), so per-key state machines never see reordering.",
            *self._evidence("component.py::PartitionedLog"))

        fan = FanoutBroker()
        a, b = fan.subscribe("a"), fan.subscribe("b")
        for i in range(5):
            fan.publish(i)
        assert a == b == list(range(5))
        findings[1] = self.satisfied(
            items[1],
            "The fan-out broker delivers every message to every subscriber, identical and complete.",
            *self._evidence("component.py::FanoutBroker"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        log = PartitionedLog(partitions=1)
        for i in range(6):
            log.append("k", i)
        log.poll("c1", 0)
        log.poll("c2", 0, limit=2)
        log.seek("c1", 0, 3)
        replay = [m for _, m in log.poll("c1", 0)]
        assert replay == [3, 4, 5] and log.offsets[("c2", 0)] == 2
        findings[0] = self.satisfied(
            items[0],
            "A consumer can rewind and replay from a retained offset after a bad deploy, and doing so "
            "leaves every other consumer's position untouched.",
            *self._evidence("component.py::PartitionedLog.seek"))
        return findings

COMPONENT = BrokerImplementationsComponent
