"""INV-59 - Application authorization.

Application authorization answers one question per call: may this identity perform this operation on this resource? The answer defaults to no, an explicit deny beats any allow, and every decision -- including the reason -- is recorded so a refusal can be explained and an allow can be audited.

The component answers all 100 requirements of the INV-59 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import fnmatch
from dataclasses import dataclass, field


@dataclass
class Policy:
    version: str
    rules: list          # (effect, identity_glob, operation_glob, resource_glob)
    records: list = field(default_factory=list)

    def decide(self, identity, operation: str, resource: str) -> dict:
        if not identity:
            d = {"allow": False, "reason": "no identity"}
        else:
            matched = [r for r in self.rules
                       if fnmatch.fnmatchcase(identity, r[1]) and fnmatch.fnmatchcase(operation, r[2])
                       and fnmatch.fnmatchcase(resource, r[3])]
            denies = [r for r in matched if r[0] == "deny"]
            if denies:
                d = {"allow": False, "reason": f"denied by {denies[0][1:]}"}
            elif matched:
                d = {"allow": True, "reason": f"allowed by {matched[0][1:]}"}
            else:
                d = {"allow": False, "reason": "no rule matched (default deny)"}
        d.update(identity=identity, operation=operation, resource=resource, policy=self.version)
        self.records.append(d)
        return d


class ApplicationAuthorizationComponent(Component):
    """Master-applied component for INV-59."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = Policy("v7", [
            ("allow", "svc:orders", "*", "db/orders/*"),
            ("deny", "*", "delete", "db/orders/audit*"),
        ])
        assert p.decide("svc:orders", "read", "db/orders/42")["allow"]
        assert not p.decide("svc:orders", "delete", "db/orders/audit-log")["allow"]
        assert not p.decide("svc:marketing", "read", "db/orders/42")["allow"]
        assert not p.decide(None, "read", "db/orders/42")["allow"]
        findings[0] = self.satisfied(
            items[0],
            "Evaluation is default-deny with deny precedence: the orders service reads its data, but a "
            "broad allow cannot override the targeted deny on the audit log, an unlisted service gets "
            "nothing, and an anonymous call is refused outright.",
            *self._evidence("component.py::Policy.decide"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        p = Policy("v8", [("allow", "svc:a", "read", "*")])
        p.decide("svc:a", "read", "x")
        p.decide("svc:b", "read", "x")
        assert all(r["reason"] and r["policy"] == "v8" for r in p.records)
        findings[0] = self.satisfied(
            items[0],
            "Every decision -- allow or deny -- is recorded with its reason and the policy version that "
            "made it, so a refusal can be explained and an allow can be audited later.",
            *self._evidence("component.py::Policy.decide"))
        return findings

COMPONENT = ApplicationAuthorizationComponent
