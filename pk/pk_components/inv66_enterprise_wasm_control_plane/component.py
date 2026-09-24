"""INV-66 - Enterprise Wasm control plane.

The enterprise Wasm control plane sits above many lattices and many teams. It adds what a single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry never reaches a deployment manager.

The component answers all 100 requirements of the INV-66 checklist.  Bands
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


@dataclass
class ControlPlane:
    roles: dict                                   # (user, lattice) -> role
    registries: frozenset
    signers: frozenset
    audit: list = field(default_factory=list)
    forwarded: list = field(default_factory=list)

    def _record(self, entry: dict) -> None:
        prev = self.audit[-1]["hash"] if self.audit else "0" * 64
        body = json.dumps(entry, sort_keys=True)
        self.audit.append({"entry": entry, "prev": prev,
                           "hash": hashlib.sha256((prev + body).encode()).hexdigest()})

    def verify_audit(self) -> bool:
        prev = "0" * 64
        for rec in self.audit:
            body = json.dumps(rec["entry"], sort_keys=True)
            if rec["prev"] != prev or rec["hash"] != hashlib.sha256((prev + body).encode()).hexdigest():
                return False
            prev = rec["hash"]
        return True

    def admit(self, user: str, lattice: str, manifest: dict) -> dict:
        reasons = []
        if self.roles.get((user, lattice)) not in ("deployer", "admin"):
            reasons.append(f"{user} may not deploy to {lattice}")
        for c in manifest["components"]:
            registry = c["image"].split("/")[0]
            if registry not in self.registries:
                reasons.append(f"{c['name']}: registry {registry} not approved")
            if c.get("signer") not in self.signers:
                reasons.append(f"{c['name']}: signer {c.get('signer')!r} not approved")
        decision = {"user": user, "lattice": lattice, "admitted": not reasons, "reasons": reasons}
        self._record(decision)
        if not reasons:
            self.forwarded.append(manifest)
        return decision


class EnterpriseWasmControlPlaneComponent(Component):
    """Master-applied component for INV-66."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _cp(self):
        return ControlPlane(roles={("dev", "staging"): "deployer", ("ops", "prod"): "deployer"},
                            registries=frozenset({"registry.estate.local"}),
                            signers=frozenset({"release-signer"}))

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        cp = self._cp()
        good = {"components": [{"name": "api", "image": "registry.estate.local/api:1", "signer": "release-signer"}]}
        evil = {"components": [{"name": "api", "image": "ghcr.evil.example/api:1", "signer": "someone"}]}
        assert cp.admit("ops", "prod", good)["admitted"]
        assert not cp.admit("dev", "prod", good)["admitted"]
        d = cp.admit("ops", "prod", evil)
        assert not d["admitted"] and len(d["reasons"]) == 2 and cp.forwarded == [good]
        findings[0] = self.satisfied(
            items[0],
            "Admission enforces role per lattice and approved registries and signers: a developer cannot "
            "deploy to prod, a manifest from an unapproved registry with an unknown signer is refused "
            "with both reasons, and only the admitted manifest is forwarded.",
            *self._evidence("component.py::ControlPlane.admit"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        cp = self._cp()
        m = {"components": [{"name": "a", "image": "registry.estate.local/a:1", "signer": "release-signer"}]}
        cp.admit("ops", "prod", m)
        cp.admit("dev", "prod", m)
        ok = cp.verify_audit()
        cp.audit[1]["entry"]["admitted"] = True          # rewrite history
        assert ok and not cp.verify_audit()
        findings[0] = self.satisfied(
            items[0],
            "Every admission and refusal is appended to a hash-chained audit log; rewriting a refusal "
            "into an admission after the fact breaks the chain and is detected.",
            *self._evidence("component.py::ControlPlane._record", "component.py::ControlPlane.verify_audit"))
        return findings

COMPONENT = EnterpriseWasmControlPlaneComponent
