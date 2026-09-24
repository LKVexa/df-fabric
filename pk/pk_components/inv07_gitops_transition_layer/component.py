"""INV-07 - GitOps transition layer.

The GitOps transition layer makes a git repository the source of desired state: a controller applies whatever the approved branch says, reverts changes made behind its back, and reports them. It only follows commits signed by an allowed key, and rolling back means reverting a commit -- so every change to the estate has an author, a review and an undo.

The component answers all 100 requirements of the INV-07 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
import hmac
from dataclasses import dataclass, field


def sign(key: bytes, state: dict) -> str:
    return hmac.new(key, repr(sorted(state.items())).encode(), hashlib.sha256).hexdigest()


class Unsigned(PermissionError):
    pass


@dataclass
class GitOps:
    keys: dict                                      # key id -> secret
    commits: list = field(default_factory=list)     # (sha, state, key_id, sig)
    live: dict = field(default_factory=dict)
    reports: list = field(default_factory=list)
    applied: list = field(default_factory=list)

    def commit(self, state: dict, key_id: str, sig: str) -> str:
        sha = hashlib.sha1(repr((len(self.commits), sorted(state.items()))).encode()).hexdigest()[:10]
        self.commits.append((sha, dict(state), key_id, sig))
        return sha

    def sync(self) -> str:
        sha, state, key_id, sig = self.commits[-1]
        key = self.keys.get(key_id)
        if key is None or not hmac.compare_digest(sig, sign(key, state)):
            raise Unsigned(f"commit {sha} is not signed by an allowed key")
        drift = {k: v for k, v in self.live.items() if state.get(k) != v}
        drift.update({k: None for k in state if k not in self.live})
        if self.applied and drift:
            self.reports.append({"commit": sha, "reverted": sorted(drift)})
        self.live = dict(state)
        self.applied.append(sha)
        return sha

    def revert(self, key_id: str) -> str:
        prev = self.commits[-2][1]
        return self.commit(prev, key_id, sign(self.keys[key_id], prev))


class GitopsTransitionLayerComponent(Component):
    """Master-applied component for INV-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        g = GitOps({"release": b"k1"})
        g.commit({"api": "v1"}, "release", sign(b"k1", {"api": "v1"}))
        g.sync()
        g.commit({"api": "evil"}, "release", sign(b"stolen-guess", {"api": "evil"}))
        refused = False
        try:
            g.sync()
        except Unsigned:
            refused = True
        assert refused and g.live == {"api": "v1"}
        findings[0] = self.satisfied(
            items[0],
            "The controller applies only commits signed by an allowed key: a commit with a bad signature "
            "is refused and the live state stays on the last verified commit.",
            *self._evidence("component.py::GitOps.sync"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        g = GitOps({"r": b"k"})
        g.commit({"api": "v1", "replicas": 3}, "r", sign(b"k", {"api": "v1", "replicas": 3}))
        g.sync()
        g.live["replicas"] = 9                     # manual hotfix behind git's back
        g.sync()
        assert g.live["replicas"] == 3 and g.reports[-1]["reverted"] == ["replicas"]
        g.commit({"api": "v2", "replicas": 3}, "r", sign(b"k", {"api": "v2", "replicas": 3}))
        g.sync()
        g.revert("r")
        g.sync()
        assert g.live["api"] == "v1" and len(g.applied) == 4
        findings[0] = self.satisfied(
            items[0],
            "A manual change made behind git's back is reverted on the next sync and reported by name; "
            "rolling back from v2 is a signed revert commit, so the rollback has its own history entry.",
            *self._evidence("component.py::GitOps.sync", "component.py::GitOps.revert"))
        return findings

COMPONENT = GitopsTransitionLayerComponent
