"""INV-69 - Agentic workload layer.

The agentic workload layer runs model-driven agents that plan and call tools. What makes that safe to operate is containment at the plan level: each agent has an allowlist of tools, a step budget, and any tool with side effects waits for a recorded approval before it runs. Every step lands in a transcript, so what an agent did is always reconstructable.

The component answers all 100 requirements of the INV-69 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

TOOLS = {
    "search_docs": {"side_effect": False, "risk": "low"},
    "run_python": {"side_effect": False, "risk": "high"},
    "send_email": {"side_effect": True, "risk": "low"},
    "delete_records": {"side_effect": True, "risk": "high"},
}


@dataclass
class Agent:
    name: str
    allow: frozenset
    max_steps: int = 10
    approvals: set = field(default_factory=set)
    transcript: list = field(default_factory=list)

    def step(self, tool: str, arg) -> dict:
        n = sum(1 for s in self.transcript if s["outcome"] in ("ran", "pending"))
        if n >= self.max_steps:
            out = {"outcome": "refused", "reason": "step budget exhausted"}
        elif tool not in self.allow or tool not in TOOLS:
            out = {"outcome": "refused", "reason": f"{tool} not in allowlist"}
        elif TOOLS[tool]["side_effect"] and (tool, arg) not in self.approvals:
            out = {"outcome": "pending", "reason": "awaiting approval"}
        else:
            tier = "heavy" if TOOLS[tool]["risk"] == "high" else "fast"
            out = {"outcome": "ran", "sandbox": tier}
        out.update(step=len(self.transcript), tool=tool, arg=arg)
        self.transcript.append(out)
        return out

    def approve(self, tool: str, arg, approver: str) -> None:
        self.approvals.add((tool, arg))
        self.transcript.append({"outcome": "approved", "tool": tool, "arg": arg, "by": approver,
                                "step": len(self.transcript)})


class AgenticWorkloadLayerComponent(Component):
    """Master-applied component for INV-69."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a = Agent("support-bot", frozenset({"search_docs", "send_email", "run_python"}))
        injected = a.step("delete_records", "all")
        held = a.step("send_email", "customer-9")
        a.approve("send_email", "customer-9", "alice")
        sent = a.step("send_email", "customer-9")
        code = a.step("run_python", "print(1)")
        assert injected["outcome"] == "refused" and held["outcome"] == "pending"
        assert sent["outcome"] == "ran" and code["sandbox"] == "heavy"
        findings[0] = self.satisfied(
            items[0],
            "An injected call to a tool outside the allowlist is refused; a side-effectful email is held "
            "until an approval is recorded (by alice) and only then runs; arbitrary code is routed to the "
            "heavy sandbox tier because of its risk class.",
            *self._evidence("component.py::Agent.step", "component.py::TOOLS"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a = Agent("looper", frozenset({"search_docs"}), max_steps=5)
        outcomes = [a.step("search_docs", i)["outcome"] for i in range(8)]
        assert outcomes.count("ran") == 5 and outcomes[5:] == ["refused"] * 3
        findings[0] = self.satisfied(
            items[0],
            "A looping agent is stopped at its step budget: five steps run and every further step is "
            "refused and recorded, so a runaway plan cannot consume unbounded resources.",
            *self._evidence("component.py::Agent.step"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        a = Agent("x", frozenset({"send_email"}))
        a.step("send_email", 1)
        a.approve("send_email", 1, "bob")
        a.step("send_email", 1)
        a.step("nope", 0)
        kinds = [s["outcome"] for s in a.transcript]
        assert kinds == ["pending", "approved", "ran", "refused"]
        assert [s["step"] for s in a.transcript] == [0, 1, 2, 3]
        findings[0] = self.satisfied(
            items[0],
            "The transcript records every step in order -- pending, approval with its approver, the run, "
            "and the refusal -- so what an agent did is reconstructable without trusting the agent.",
            *self._evidence("component.py::Agent.transcript"))
        return findings

COMPONENT = AgenticWorkloadLayerComponent
