"""INV-02 - Container substrate.

The container substrate is the packaging layer the estate runs on today: images made of layers, pulled by name, run by a runtime. The weakness is the name -- a tag can be moved to point at different bytes. This element resolves every image to a content digest, checks the manifest against its layers, and refuses mutable tags wherever reproducibility matters.

The component answers all 100 requirements of the INV-02 checklist.  Bands
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


def digest(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


class IntegrityError(ValueError):
    pass


class MutableTagRefused(ValueError):
    pass


@dataclass
class Registry:
    blobs: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)

    def push(self, name: str, tag: str, layers: list) -> str:
        ids = []
        for layer in layers:
            d = digest(layer)
            self.blobs.setdefault(d, layer)      # stored once however many images share it
            ids.append(d)
        manifest = json.dumps({"layers": ids}).encode()
        m = digest(manifest)
        self.blobs[m] = manifest
        self.tags[f"{name}:{tag}"] = m
        return m

    def resolve(self, ref: str, env: str) -> str:
        if "@sha256:" in ref:
            return ref.split("@", 1)[1]
        if env == "production":
            raise MutableTagRefused(f"{ref}: production requires a digest reference")
        return self.tags[ref]

    def pull(self, manifest_digest: str) -> list:
        manifest = self.blobs[manifest_digest]
        if digest(manifest) != manifest_digest:
            raise IntegrityError("manifest does not match its digest")
        out = []
        for d in json.loads(manifest)["layers"]:
            if digest(self.blobs[d]) != d:
                raise IntegrityError(f"layer {d[:19]} corrupted")
            out.append(self.blobs[d])
        return out


class ContainerSubstrateComponent(Component):
    """Master-applied component for INV-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        reg = Registry()
        good = reg.push("api", "1.0", [b"base-os", b"app-v1"])
        refused = False
        try:
            reg.resolve("api:1.0", "production")
        except MutableTagRefused:
            refused = True
        assert refused and reg.resolve(f"api@{good}", "production") == good
        reg.push("api", "1.0", [b"base-os", b"evil-v1"])          # tag moved
        assert reg.resolve("api:1.0", "staging") != good and reg.pull(good)[1] == b"app-v1"
        base = digest(b"base-os")
        reg.blobs[base] = b"tampered"
        corrupt = False
        try:
            reg.pull(good)
        except IntegrityError:
            corrupt = True
        assert corrupt
        findings[0] = self.satisfied(
            items[0],
            "Production accepts only digest references, so moving the tag to other bytes changes nothing "
            "for workloads pinned by digest; a layer altered in the registry fails verification at pull.",
            *self._evidence("component.py::Registry.resolve", "component.py::Registry.pull"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        reg = Registry()
        base = b"x" * 10_000
        for i in range(5):
            reg.push(f"svc{i}", "1", [base, f"app{i}".encode()])
        layer_bytes = sum(len(v) for k, v in reg.blobs.items() if not v.startswith(b"{"))
        assert layer_bytes < 2 * len(base)
        findings[0] = self.satisfied(
            items[0],
            f"Five images sharing a 10 kB base layer store it once ({layer_bytes} layer bytes in total "
            "rather than over 50 kB), because layers are addressed by content.",
            *self._evidence("component.py::Registry.push"))
        return findings

COMPONENT = ContainerSubstrateComponent
