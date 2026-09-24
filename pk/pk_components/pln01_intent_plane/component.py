"""PLN-01 - Intent plane.

The intent plane holds the desired state of the estate as a live graph rather than as disconnected Terraform state and Kubernetes YAML. It accepts declarations, resolves them into a dependency-ordered reconciliation plan, and hands that plan to the planes below. It never executes: planning and execution are deliberately separated.

The component answers all 100 requirements of the PLN-01 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


class CycleError(ValueError):
    """Raised when the declared graph cannot be totally ordered."""


class IntentGraph:
    """The authoritative desired-state graph.

    Nodes are addressed by ``(tenant, environment, name)``.  Edges express
    "must be reconciled after", so a plan is a topological order of the graph.
    """

    def __init__(self):
        self._nodes: dict[tuple, dict] = {}
        self._edges: dict[tuple, set] = {}
        self.version = 0

    def declare(self, tenant: str, environment: str, name: str, spec: dict, after=()):
        key = (tenant, environment, name)
        for dep in after:
            if dep[0] != tenant:
                raise PermissionError(f"cross-tenant edge refused: {key} -> {dep}")
        self._nodes[key] = dict(spec)
        self._edges[key] = set(after)
        self.version += 1
        return key

    def retract(self, key):
        self._nodes.pop(key, None)
        self._edges.pop(key, None)
        for deps in self._edges.values():
            deps.discard(key)
        self.version += 1

    def __len__(self):
        return len(self._nodes)

    def order(self) -> list:
        """Return a deterministic topological order, or raise :class:`CycleError`."""
        pending = {k: set(v) & set(self._nodes) for k, v in self._edges.items()}
        out: list = []
        while pending:
            ready = sorted(k for k, deps in pending.items() if not deps)
            if not ready:
                raise CycleError(f"dependency cycle among {sorted(pending)}")
            for key in ready:
                out.append(key)
                del pending[key]
            for deps in pending.values():
                deps.difference_update(ready)
        return out

    def drift(self, actual: dict) -> list:
        """Return nodes whose reported actual state differs from intent."""
        drifted = []
        for key, spec in sorted(self._nodes.items()):
            if actual.get(key) != spec:
                drifted.append(key)
        return drifted


def plan(graph: IntentGraph, actual: dict | None = None) -> dict:
    """Produce a dry-run reconciliation plan for ``graph``."""
    actual = actual or {}
    order = graph.order()
    steps = [
        {"step": n, "node": list(key), "action": "create" if key not in actual else
         ("update" if actual[key] != graph._nodes[key] else "noop")}
        for n, key in enumerate(order, 1)
    ]
    return {
        "schema": "PK_RECONCILIATION_PLAN/1",
        "graph_version": graph.version,
        "dry_run": True,
        "steps": steps,
        "drift": [list(k) for k in graph.drift(actual)],
    }


class IntentPlaneComponent(Component):
    """Master-applied component for PLN-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        """Exercise the graph and planner rather than asserting they exist."""
        findings = super().assess_implementation(items)
        graph = IntentGraph()
        a = graph.declare("t1", "prod", "network", {"cidr": "10.0.0.0/16"})
        b = graph.declare("t1", "prod", "runtime", {"kind": "wasm"}, after=[a])
        graph.declare("t1", "prod", "app", {"image": "svc:1"}, after=[b])
        order = graph.order()
        assert order.index(a) < order.index(b), "planner did not honour declared order"
        dry = plan(graph, actual={a: {"cidr": "10.0.0.0/16"}})
        assert dry["dry_run"] is True and len(dry["steps"]) == 3
        findings[5] = self.satisfied(
            items[5],
            f"Planner is deterministic: {len(order)} nodes ordered, "
            f"{sum(1 for s in dry['steps'] if s['action'] == 'noop')} step(s) resolved to noop.",
            *self._evidence("component.py::plan"),
        )
        try:
            cyclic = IntentGraph()
            x = cyclic.declare("t1", "prod", "x", {})
            y = cyclic.declare("t1", "prod", "y", {}, after=[x])
            cyclic._edges[x].add(y)
            cyclic.order()
        except CycleError:
            findings[6] = self.satisfied(
                items[6], "Dependency cycles are reported, not silently reordered.",
                *self._evidence("component.py::IntentGraph.order"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        graph = IntentGraph()
        foreign = ("t2", "prod", "shared")
        try:
            graph.declare("t1", "prod", "app", {}, after=[foreign])
        except PermissionError:
            findings[5] = self.satisfied(
                items[5], "Cross-tenant graph edges are refused at declaration time.",
                *self._evidence("component.py::IntentGraph.declare"))
        return findings

COMPONENT = IntentPlaneComponent
