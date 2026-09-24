"""INV-58 - Existing service-mesh layer.

The existing service-mesh layer is already doing mTLS, retries and routing for current workloads, and the new runtime has to coexist with it rather than duplicate it. The sharpest hazard is retry multiplication: three app retries through a mesh that also retries three times is nine attempts against a struggling service. This element owns the division of labour.

The component answers all 100 requirements of the INV-58 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class Unmappable(ValueError):
    pass


def effective_attempts(app_attempts: int, mesh_attempts: int) -> int:
    return app_attempts * mesh_attempts


def reconcile(route: str, app_attempts: int, mesh_attempts: int, budget: int = 3) -> dict:
    """Give retries to one layer and keep total attempts inside the budget."""
    if effective_attempts(app_attempts, mesh_attempts) <= budget:
        owner = "both" if app_attempts > 1 and mesh_attempts > 1 else (
            "app" if app_attempts > 1 else "mesh" if mesh_attempts > 1 else "none")
        return {"route": route, "owner": owner, "app": app_attempts, "mesh": mesh_attempts}
    # The runtime knows idempotency keys; the mesh does not.  Prefer the app layer.
    return {"route": route, "owner": "app", "app": min(app_attempts, budget), "mesh": 1}


def map_identity(san: str, trust_domain: str) -> str:
    prefix = f"spiffe://{trust_domain}/"
    if not san.startswith(prefix):
        raise Unmappable(f"{san} is not in trust domain {trust_domain}")
    return "runtime:" + san[len(prefix):]


@dataclass
class BypassDetector:
    meshed: set = field(default_factory=set)
    flagged: list = field(default_factory=list)

    def observe(self, src: str, dst: str, mtls: bool) -> bool:
        bypass = dst in self.meshed and not mtls
        if bypass:
            self.flagged.append((src, dst))
        return bypass


class ExistingServiceMeshLayerComponent(Component):
    """Master-applied component for INV-58."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        naive = effective_attempts(3, 3)
        r = reconcile("orders->payments", 3, 3, budget=3)
        total = effective_attempts(r["app"], r["mesh"])
        assert naive == 9 and total == 3 and r["owner"] == "app"
        findings[0] = self.satisfied(
            items[0],
            f"Left alone, 3 app retries through 3 mesh retries is {naive} attempts per call; "
            f"reconciliation hands retries to the app layer (which holds idempotency keys) and sets mesh "
            f"retries to 1, so the call gets {total} attempts, inside its budget.",
            *self._evidence("component.py::reconcile"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        assert map_identity("spiffe://estate.local/ns/shop/sa/orders", "estate.local") == "runtime:ns/shop/sa/orders"
        foreign = False
        try:
            map_identity("spiffe://evil.example/ns/shop/sa/orders", "estate.local")
        except Unmappable:
            foreign = True
        det = BypassDetector({"payments"})
        assert foreign and det.observe("legacy-cron", "payments", mtls=False) and not det.observe("orders", "payments", True)
        findings[0] = self.satisfied(
            items[0],
            "Mesh certificate identities map into runtime identities only from the estate's own trust "
            "domain, and plaintext traffic to a meshed service is flagged as a bypass.",
            *self._evidence("component.py::map_identity", "component.py::BypassDetector"))
        return findings

COMPONENT = ExistingServiceMeshLayerComponent
