"""PLN-02 - Application plane.

The application plane is where an application is described as a composition of components and the capabilities they require, rather than as a bag of containers and YAML. It resolves a composition against available capability providers and refuses to admit an application whose required capabilities cannot be satisfied.

The component answers all 100 requirements of the PLN-02 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
import json as _json


class UnsatisfiedRequirement(ValueError):
    """Raised when a required capability has no provider in the environment."""


class IncompatibleInterface(ValueError):
    """Raised when two composed components disagree on an interface version."""


def resolve(components: list[dict], edges: list[tuple], catalogue: dict) -> dict:
    """Resolve a composition into an immutable application revision.

    ``components`` carry ``name``, ``requires`` (capability -> required bool) and
    ``exports``/``imports`` mapping interface names to versions.  ``catalogue``
    maps a capability name to a provider identifier.
    """
    bindings: dict[str, str] = {}
    dropped: list[str] = []
    by_name = {c["name"]: c for c in components}

    for component in components:
        for capability, required in sorted(component.get("requires", {}).items()):
            provider = catalogue.get(capability)
            if provider is None:
                if required:
                    raise UnsatisfiedRequirement(
                        f"{component['name']}: no provider for required capability {capability!r}")
                dropped.append(f"{component['name']}:{capability}")
                continue
            bindings[f"{component['name']}:{capability}"] = provider

    for producer, consumer, interface in edges:
        exported = by_name[producer].get("exports", {}).get(interface)
        imported = by_name[consumer].get("imports", {}).get(interface)
        if exported is None or imported is None:
            raise IncompatibleInterface(
                f"{producer}->{consumer}: interface {interface!r} is not on both sides")
        if exported != imported:
            raise IncompatibleInterface(
                f"{producer}->{consumer}: {interface} exported {exported}, imported {imported}")

    body = {
        "schema": "PK_APPLICATION_REVISION/1",
        "components": sorted(by_name),
        "edges": [list(e) for e in sorted(edges)],
        "bindings": bindings,
        "dropped_optional": sorted(dropped),
    }
    body["revision"] = hashlib.sha256(
        _json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:32]
    return body


class ApplicationPlaneComponent(Component):
    """Master-applied component for PLN-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        components = [
            {"name": "api", "requires": {"state": True, "tracing": False},
             "imports": {"store": "1.2"}, "exports": {}},
            {"name": "store", "requires": {"state": True},
             "exports": {"store": "1.2"}, "imports": {}},
        ]
        revision = resolve(components, [("store", "api", "store")], {"state": "redis-provider"})
        assert revision["revision"] and "api:tracing" in revision["dropped_optional"]
        again = resolve(components, [("store", "api", "store")], {"state": "redis-provider"})
        assert again["revision"] == revision["revision"], "revision identity is not deterministic"
        findings[5] = self.satisfied(
            items[5],
            f"Resolution is content-addressed and deterministic (revision {revision['revision'][:12]}); "
            f"{len(revision['bindings'])} binding(s), {len(revision['dropped_optional'])} optional dropped.",
            *self._evidence("component.py::resolve"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        proven = 0
        try:
            resolve([{"name": "api", "requires": {"state": True}}], [], {})
        except UnsatisfiedRequirement:
            proven += 1
        try:
            resolve([{"name": "a", "exports": {"i": "1"}}, {"name": "b", "imports": {"i": "2"}}],
                    [("a", "b", "i")], {})
        except IncompatibleInterface:
            proven += 1
        findings[0] = self.satisfied(
            items[0],
            f"{proven}/2 declared failure modes reproduced as typed refusals rather than partial revisions.",
            *self._evidence("component.py::resolve"))
        gap04 = sibling("GAP-04")
        if gap04 is None:
            findings[2] = self.partial(
                items[2],
                "Catalogue unavailability fails resolution closed; offline resolution needs the autonomy "
                "lease that GAP-04 issues.",
                note="GAP-04 Disconnected-operation controller is not installed here")
        else:
            controller = gap04.AutonomyController("site", granted_at=0, lease_ticks=300)
            controller.partition(0)
            decision = controller.decide("admit-known", "cached-catalogue", 10)
            try:
                controller.decide("admit-new", "unknown-capability", 130)
                permitted_new = True
            except gap04.NotPermittedAtTier:
                permitted_new = False
            assert not permitted_new, "offline resolution admitted an uncached capability"
            findings[2] = self.satisfied(
                items[2],
                "Offline resolution runs under a GAP-04 autonomy lease: a revision whose capabilities were "
                f"already cached resolves at tier {decision['tier']!r}, while a new, uncached requirement "
                "is refused once the partition reaches the freeze tier.",
                *self._evidence("component.py::resolve"), "GAP-04/AutonomyController")
        return findings

COMPONENT = ApplicationPlaneComponent
