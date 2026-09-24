"""INV-70 - Fast agent sandbox.

The fast agent sandbox runs small pieces of untrusted logic in microseconds: a tiny stack machine with a fuel counter, a hard memory ceiling, and no host access except through capabilities the agent was granted. It is fast because it is small, and safe because a program that runs out of fuel, memory or permissions simply stops with a reason.

The component answers all 100 requirements of the INV-70 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


class Trap(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def run(program, fuel=1000, max_stack=64, caps=frozenset(), host=None):
    """Stack machine: push n | add | mul | dup | jmp n | jz n | call name | halt."""
    host = host or {}
    stack, pc, used = [], 0, 0
    try:
        while True:
            if used >= fuel:
                raise Trap("out of fuel")
            used += 1
            if not 0 <= pc < len(program):
                raise Trap("pc out of range")
            op, *arg = program[pc]
            pc += 1
            if op == "push":
                stack.append(arg[0])
            elif op == "add":
                stack.append(stack.pop() + stack.pop())
            elif op == "mul":
                stack.append(stack.pop() * stack.pop())
            elif op == "dup":
                stack.append(stack[-1])
            elif op == "jmp":
                pc = arg[0]
            elif op == "jz":
                if stack.pop() == 0:
                    pc = arg[0]
            elif op == "call":
                if arg[0] not in caps:
                    raise Trap(f"capability denied: {arg[0]}")
                stack.append(host[arg[0]](stack.pop()))
            elif op == "halt":
                return {"ok": stack[-1] if stack else None, "fuel": used}
            else:
                raise Trap(f"invalid instruction {op}")
            if len(stack) > max_stack:
                raise Trap("out of memory")
    except Trap as t:
        return {"trap": t.reason, "fuel": used}
    except IndexError:
        return {"trap": "stack underflow", "fuel": used}


class FastAgentSandboxComponent(Component):
    """Master-applied component for INV-70."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        spin = run([("jmp", 0)], fuel=500)
        bomb = run([("push", 1), ("dup",), ("jmp", 1)], fuel=10_000, max_stack=32)
        escape = run([("push", "/etc/passwd"), ("call", "read_file"), ("halt",)],
                     host={"read_file": lambda p: "root:x"})
        allowed = run([("push", 3), ("call", "double"), ("halt",)], caps={"double"},
                      host={"double": lambda x: 2 * x})
        assert spin == {"trap": "out of fuel", "fuel": 500}
        assert bomb["trap"] == "out of memory"
        assert escape["trap"] == "capability denied: read_file" and allowed["ok"] == 6
        findings[0] = self.satisfied(
            items[0],
            "An infinite loop stops at exactly its 500 fuel, a stack bomb stops at the memory ceiling, "
            "and a host call without a granted capability traps before the host function is reached, "
            "while a granted one works.",
            *self._evidence("component.py::run"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        prog = [("push", 2), ("push", 3), ("mul",), ("push", 4), ("add",), ("halt",)]
        r = run(prog)
        assert r == {"ok": 10, "fuel": 6}
        findings[0] = self.satisfied(
            items[0],
            "Fuel is metered per instruction, so cost is exact and predictable: this 6-instruction "
            "program returns 10 having used exactly 6 units.",
            *self._evidence("component.py::run"))
        return findings

COMPONENT = FastAgentSandboxComponent
