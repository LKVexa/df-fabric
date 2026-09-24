"""INV-68 - Resource packing.

Resource packing decides how many workloads fit on how many hosts. Packing well means fewer hosts for the same work; packing carelessly means one dimension -- usually memory -- runs out while CPU sits idle. The packer places across every dimension at once, keeps a headroom reserve, and reports the fragmentation it leaves behind.

The component answers all 100 requirements of the INV-68 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import math
from dataclasses import dataclass, field

OVERCOMMIT = {"cpu": 1.5, "mem": 1.0}      # memory is never overcommitted


@dataclass
class Host:
    name: str
    cpu: float
    mem: float
    used: dict = field(default_factory=lambda: {"cpu": 0.0, "mem": 0.0})

    def limit(self, dim: str, headroom: float) -> float:
        return getattr(self, dim) * OVERCOMMIT[dim] * (1 - headroom)

    def fits(self, w: dict, headroom: float) -> bool:
        return all(self.used[d] + w[d] <= self.limit(d, headroom) + 1e-9 for d in ("cpu", "mem"))


def pack(workloads, host_cpu, host_mem, headroom=0.1):
    order = sorted(workloads, key=lambda w: max(w["cpu"] / host_cpu, w["mem"] / host_mem), reverse=True)
    hosts, unplaced = [], []
    for w in order:
        if w["cpu"] > host_cpu * OVERCOMMIT["cpu"] * (1 - headroom) or w["mem"] > host_mem * (1 - headroom):
            unplaced.append(w["name"])
            continue
        target = next((h for h in hosts if h.fits(w, headroom)), None)
        if target is None:
            target = Host(f"h{len(hosts)}", host_cpu, host_mem)
            hosts.append(target)
        for d in ("cpu", "mem"):
            target.used[d] += w[d]
        w["host"] = target.name
    return hosts, unplaced


def lower_bound(workloads, host_cpu, host_mem, headroom=0.1) -> int:
    return max(math.ceil(sum(w[d] for w in workloads) / (cap * OVERCOMMIT[d] * (1 - headroom)))
               for d, cap in (("cpu", host_cpu), ("mem", host_mem)))


def fragmentation(hosts, headroom=0.1) -> dict:
    return {d: round(sum(h.limit(d, headroom) - h.used[d] for h in hosts), 3) for d in ("cpu", "mem")}


class ResourcePackingComponent(Component):
    """Master-applied component for INV-68."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _work(self):
        import random
        rng = random.Random(7)
        return [{"name": f"w{i}", "cpu": rng.choice([0.5, 1, 2, 4]), "mem": rng.choice([1, 2, 4, 8])}
                for i in range(60)]

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        work = self._work()
        hosts, unplaced = pack(work, host_cpu=16, host_mem=64)
        lb = lower_bound(work, 16, 64)
        naive = len(work)
        assert not unplaced and len(hosts) <= math.ceil(lb * 1.1) + 1
        findings[0] = self.satisfied(
            items[0],
            f"Sixty mixed workloads pack onto {len(hosts)} hosts against a theoretical lower bound of "
            f"{lb} (one-per-host would need {naive}); fragmentation left behind is "
            f"{fragmentation(hosts)}, reported rather than hidden.",
            *self._evidence("component.py::pack", "component.py::lower_bound"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        hosts, unplaced = pack(self._work() + [{"name": "whale", "cpu": 1, "mem": 60}], 16, 64, headroom=0.1)
        worst_mem = max(h.used["mem"] / h.mem for h in hosts)
        assert "whale" in unplaced and worst_mem <= 0.9 + 1e-9
        findings[0] = self.satisfied(
            items[0],
            f"Memory is never overcommitted and every host keeps its 10% headroom (peak memory use "
            f"{worst_mem:.0%}); a workload that could only fit by eating the headroom is reported "
            "unplaced instead.",
            *self._evidence("component.py::Host.fits", "component.py::OVERCOMMIT"))
        return findings

COMPONENT = ResourcePackingComponent
