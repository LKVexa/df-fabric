"""INV-61 - Distributed WIT RPC.

Distributed WIT RPC carries typed interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments.

The component answers all 100 requirements of the INV-61 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
import json
from dataclasses import dataclass, field


def fingerprint(params, results) -> str:
    return hashlib.sha256(json.dumps([list(params), list(results)]).encode()).hexdigest()[:16]


class SignatureMismatch(TypeError):
    pass


@dataclass
class Endpoint:
    interface: str
    version: str
    functions: dict = field(default_factory=dict)   # name -> (params, results, impl)
    mismatches: int = 0

    def export(self, name, params, results, impl):
        self.functions[name] = (tuple(params), tuple(results), impl)

    def handle(self, frame: dict, now: int) -> dict:
        if now > frame["deadline"]:
            return {"error": "deadline-exceeded"}
        fn = self.functions.get(frame["function"])
        if frame["interface"] != self.interface or fn is None:
            return {"error": "unknown-function"}
        if frame["fp"] != fingerprint(fn[0], fn[1]):
            self.mismatches += 1
            return {"error": "signature-mismatch",
                    "detail": f"{frame['function']}@{frame['version']} vs {self.version}"}
        try:
            return {"ok": fn[2](*frame["args"])}
        except Exception as exc:
            return {"error": "callee-trap", "detail": type(exc).__name__}


def frame(interface, version, function, params, results, args, deadline) -> dict:
    return {"interface": interface, "version": version, "function": function,
            "fp": fingerprint(params, results), "args": list(args), "deadline": deadline}


class DistributedWitRpcComponent(Component):
    """Master-applied component for INV-61."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        ep = Endpoint("kv", "0.2.0")
        ep.export("get", ["string"], ["option<u64>"], lambda k: 7)
        ok = ep.handle(frame("kv", "0.2.0", "get", ["string"], ["option<u64>"], ["a"], 10), now=0)
        drift = ep.handle(frame("kv", "0.1.0", "get", ["string"], ["u64"], ["a"], 10), now=0)
        assert ok == {"ok": 7} and drift["error"] == "signature-mismatch" and ep.mismatches == 1
        findings[0] = self.satisfied(
            items[0],
            "Every frame carries a signature fingerprint that the receiver checks before decoding: a "
            "matching caller gets its result, and a caller built against an older result type gets a "
            "typed signature-mismatch error instead of a misread value.",
            *self._evidence("component.py::Endpoint.handle", "component.py::fingerprint"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        ep = Endpoint("kv", "1")
        ep.export("boom", [], [], lambda: 1 / 0)
        late = ep.handle(frame("kv", "1", "boom", [], [], [], deadline=5), now=6)
        trap = ep.handle(frame("kv", "1", "boom", [], [], [], deadline=5), now=1)
        assert late == {"error": "deadline-exceeded"} and trap["error"] == "callee-trap"
        findings[0] = self.satisfied(
            items[0],
            "A frame past its deadline is refused without running, and a callee trap comes back as a "
            "typed error rather than a hung or dropped connection.",
            *self._evidence("component.py::Endpoint.handle"))
        return findings

COMPONENT = DistributedWitRpcComponent
