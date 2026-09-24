"""INV-64 - Application model.

The application model is the declarative description of an application: its components, the providers they link to, and the traits -- scaling, spread -- attached to each. Its value is validation before anything runs: a link to a component that does not exist, a trait on a component that is not there, or a schema version the platform does not speak is refused at submit.

The component answers all 100 requirements of the INV-64 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
import json

SCHEMAS = {"app/v1"}


def validate(m: dict) -> list:
    errors = []
    if m.get("schema") not in SCHEMAS:
        errors.append(f"unsupported schema {m.get('schema')!r}")
    comps = [c["name"] for c in m.get("components", [])]
    provs = [p["name"] for p in m.get("providers", [])]
    names = comps + provs
    errors += [f"duplicate name {n!r}" for n in sorted({n for n in names if names.count(n) > 1})]
    for l in m.get("links", []):
        if l["from"] not in comps:
            errors.append(f"link from undeclared component {l['from']!r}")
        if l["to"] not in names:
            errors.append(f"link to undeclared target {l['to']!r}")
    for t in m.get("traits", []):
        if t["component"] not in comps:
            errors.append(f"trait {t['type']} on undeclared component {t['component']!r}")
    return errors


def canonical(m: dict) -> str:
    norm = dict(m)
    for key in ("components", "providers", "links", "traits"):
        norm[key] = sorted(m.get(key, []), key=lambda x: json.dumps(x, sort_keys=True))
    return hashlib.sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()


class ApplicationModelComponent(Component):
    """Master-applied component for INV-64."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        good = {"schema": "app/v1",
                "components": [{"name": "api"}, {"name": "worker"}],
                "providers": [{"name": "kv"}],
                "links": [{"from": "api", "to": "kv"}],
                "traits": [{"type": "spread", "component": "api"}]}
        bad = dict(good, schema="app/v9",
                   links=[{"from": "api", "to": "redis"}],
                   traits=[{"type": "scaler", "component": "ghost"}])
        errs = validate(bad)
        assert validate(good) == [] and len(errs) == 3
        findings[0] = self.satisfied(
            items[0],
            f"A manifest with an unknown schema, a dangling link and an orphan trait is refused at submit "
            f"with all {len(errs)} errors reported together, while the well-formed manifest validates clean.",
            *self._evidence("component.py::validate"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        a = {"schema": "app/v1", "components": [{"name": "x"}, {"name": "y"}], "links": [], "traits": [], "providers": []}
        b = dict(a, components=[{"name": "y"}, {"name": "x"}])
        c = dict(a, components=[{"name": "x"}])
        assert canonical(a) == canonical(b) != canonical(c)
        findings[0] = self.satisfied(
            items[0],
            "Manifests have a canonical digest: reordering components does not change it, removing one "
            "does, so diffing and signing operate on meaning rather than formatting.",
            *self._evidence("component.py::canonical"))
        return findings

COMPONENT = ApplicationModelComponent
