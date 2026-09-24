"""INV-72 - Accelerated workload requirement.

An accelerated workload requirement is how a job says what hardware it actually needs: which accelerator class, how much device memory, how many devices, and whether they must share a fast interconnect. Matching is strict on what matters -- a job needing 80 GB is never placed on a 40 GB part -- and device sharing is allowed only when the tenant's isolation class permits partitioning.

The component answers all 100 requirements of the INV-72 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


@dataclass
class Device:
    dev_id: str
    cls: str
    mem_gb: int
    node: str
    link_group: str
    partition_of: str = ""        # non-empty when this is a slice of a physical device
    tenants: set = field(default_factory=set)


def match(req: dict, devices: list):
    reasons = []
    cands = [d for d in devices if d.cls == req["class"]]
    if not cands:
        return None, [f"no {req['class']} devices"]
    fit = [d for d in cands if d.mem_gb >= req["mem_gb"]]
    if not fit:
        return None, [f"largest {req['class']} has {max(d.mem_gb for d in cands)} GB < {req['mem_gb']} GB"]
    ok = []
    for d in fit:
        if d.partition_of:
            if req.get("isolation") == "dedicated":
                reasons.append(f"{d.dev_id}: partition not allowed for dedicated isolation")
                continue
            if d.tenants - {req["tenant"]}:
                reasons.append(f"{d.dev_id}: partition already shared with another tenant")
                continue
        ok.append(d)
    count = req.get("count", 1)
    if req.get("interconnect"):
        groups = {}
        for d in ok:
            groups.setdefault((d.node, d.link_group), []).append(d)
        chosen = next((g[:count] for g in groups.values() if len(g) >= count), None)
        if chosen is None:
            return None, reasons + [f"no {count} devices share one interconnect"]
    else:
        chosen = ok[:count] if len(ok) >= count else None
        if chosen is None:
            return None, reasons + [f"only {len(ok)} eligible device(s), need {count}"]
    for d in chosen:
        d.tenants.add(req["tenant"])
    return [d.dev_id for d in chosen], reasons


class AcceleratedWorkloadRequirementComponent(Component):
    """Master-applied component for INV-72."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _fleet(self):
        return [Device("a0", "gpu-large", 80, "n1", "nvl-1"), Device("a1", "gpu-large", 80, "n1", "nvl-1"),
                Device("b0", "gpu-large", 80, "n2", "pcie"), Device("c0", "gpu-large", 40, "n3", "pcie"),
                Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")]

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        fleet = self._fleet()
        pair, _ = match({"class": "gpu-large", "mem_gb": 80, "count": 2, "interconnect": True,
                         "tenant": "t1", "isolation": "dedicated"}, fleet)
        big, why = match({"class": "gpu-large", "mem_gb": 120, "tenant": "t1"}, fleet)
        assert pair == ["a0", "a1"] and big is None and "80 GB < 120 GB" in why[0]
        findings[0] = self.satisfied(
            items[0],
            "A two-device job needing a shared interconnect gets the two 80 GB parts on one link group, "
            "and a job needing more memory than any part has is refused with the gap stated rather than "
            "placed to fail mid-run.",
            *self._evidence("component.py::match"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        part = [Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")]
        got, _ = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t1", "isolation": "shared"}, part)
        other, why = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t2", "isolation": "shared"}, part)
        ded, why2 = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t1", "isolation": "dedicated"},
                          [Device("p1", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")])
        assert got == ["p0"] and other is None and ded is None
        findings[0] = self.satisfied(
            items[0],
            "Partitioned devices are shared only within the rules: a slice taken by one tenant is refused "
            "to a second tenant, and a job requiring dedicated isolation is never given a slice at all.",
            *self._evidence("component.py::match"))
        return findings

COMPONENT = AcceleratedWorkloadRequirementComponent
