"""GAP-08 - OTA lifecycle/rollback.

OTA lifecycle and rollback is how an edge estate survives its own updates. Every rollout is staged, every stage has a health gate, and the rollback target is pinned before the first node is touched -- so a bad update stops at the canary instead of reaching the fleet.

The component answers all 100 requirements of the GAP-08 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class BundleRejected(PermissionError):
    """Raised when an update bundle is not verified for rollout."""


class GateFailed(RuntimeError):
    """Raised when a wave's health gate does not pass."""


class NoRollbackTarget(RuntimeError):
    """Raised when a rollout is attempted without a pinned previous version."""


@dataclass
class Rollout:
    """A staged, gated, automatically-reversible fleet update."""

    bundle: str
    waves: list                     # list of node lists, smallest first
    pinned_target: str | None = None
    verified: bool = False
    wave_index: int = 0
    versions: dict = field(default_factory=dict)      # node -> version
    deferred: list = field(default_factory=list)
    history: list = field(default_factory=list)
    rolled_back: bool = False

    def pin(self, current_versions: dict) -> str:
        """Pin the rollback target before anything is touched. Never recomputed later."""
        if self.pinned_target is not None:
            raise RuntimeError("rollback target is already pinned and may not be repointed")
        distinct = set(current_versions.values())
        if len(distinct) != 1:
            raise NoRollbackTarget(f"fleet is not on a single version: {sorted(distinct)}")
        self.pinned_target = distinct.pop()
        self.versions = dict(current_versions)
        return self.pinned_target

    def admit(self, verification: dict | None) -> None:
        if not verification or not verification.get("verified"):
            raise BundleRejected(f"{self.bundle}: not admitted without a verified signature")
        self.verified = True

    def run_wave(self, *, healthy: bool, offline=()) -> dict:
        """Apply the next wave, then gate on health. A failing gate rolls the fleet back."""
        if not self.verified:
            raise BundleRejected(f"{self.bundle}: rollout attempted before verification")
        if self.pinned_target is None:
            raise NoRollbackTarget("rollout attempted with no pinned rollback target")
        if self.rolled_back:
            raise GateFailed("rollout already rolled back; start a new rollout")
        if self.wave_index >= len(self.waves):
            return {"schema": "PK_ROLLOUT/1", "complete": True, "wave": self.wave_index}

        wave = self.waves[self.wave_index]
        touched = []
        for node in wave:
            if node in offline:
                self.deferred.append(node)
                continue
            self.versions[node] = self.bundle
            touched.append(node)
        self.wave_index += 1

        verdict = {"schema": "PK_ROLLOUT_GATE/1", "wave": self.wave_index,
                   "touched": touched, "deferred": list(self.deferred), "healthy": healthy}
        self.history.append(verdict)
        if not healthy:
            self.rollback(reason=f"health gate failed after wave {self.wave_index}")
            verdict["rolled_back"] = True
        return verdict

    def rollback(self, *, reason: str) -> dict:
        if self.pinned_target is None:
            raise NoRollbackTarget("nothing to roll back to")
        reverted = [n for n, v in self.versions.items() if v == self.bundle]
        for node in reverted:
            self.versions[node] = self.pinned_target
        self.rolled_back = True
        return {"schema": "PK_ROLLBACK/1", "target": self.pinned_target,
                "reverted": sorted(reverted), "reason": reason}

    def fleet_on(self, version: str) -> list:
        return sorted(n for n, v in self.versions.items() if v == version)


class OtaLifecycleRollbackComponent(Component):
    """Master-applied component for GAP-08."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        fleet = {f"n{i}": "v1" for i in range(1, 8)}
        r = Rollout("v2", waves=[["n1"], ["n2", "n3"], ["n4", "n5", "n6", "n7"]])
        r.pin(fleet)
        r.admit({"verified": True})
        assert r.run_wave(healthy=True)["touched"] == ["n1"]
        assert r.run_wave(healthy=True)["touched"] == ["n2", "n3"]
        r.run_wave(healthy=True)
        assert r.fleet_on("v2") == sorted(fleet), "rollout did not reach the whole fleet"
        findings[5] = self.satisfied(
            items[5],
            "Waves apply in declared order, smallest first, and a healthy rollout reaches the whole fleet "
            f"in {len(r.history)} gated steps.",
            *self._evidence("component.py::Rollout.run_wave"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        fleet = {f"n{i}": "v1" for i in range(1, 8)}
        r = Rollout("v-bad", waves=[["n1"], ["n2", "n3"], ["n4", "n5", "n6", "n7"]])
        r.pin(fleet)
        r.admit({"verified": True})
        verdict = r.run_wave(healthy=False)
        assert verdict.get("rolled_back") and r.fleet_on("v1") == sorted(fleet)
        assert r.fleet_on("v-bad") == [], "a bad update survived rollback"
        findings[1] = self.satisfied(
            items[1],
            "A failing gate after the first wave rolls the whole fleet back to the pinned target; the bad "
            "version reaches one node, not seven.",
            *self._evidence("component.py::Rollout.rollback"))
        try:
            r.run_wave(healthy=True)
        except GateFailed:
            findings[6] = self.satisfied(
                items[6],
                "A rolled-back rollout cannot be resumed; a new rollout must be started, so a bad bundle "
                "cannot be pushed past its own failure.",
                *self._evidence("component.py::Rollout.run_wave"))
        offline_run = Rollout("v2", waves=[["n1", "n2"]])
        offline_run.pin(fleet)
        offline_run.admit({"verified": True})
        result = offline_run.run_wave(healthy=True, offline={"n2"})
        assert result["deferred"] == ["n2"] and offline_run.versions["n2"] == "v1"
        findings[2] = self.satisfied(
            items[2],
            "A node offline during its wave is deferred and left on the old version rather than counted as "
            "updated.",
            *self._evidence("component.py::Rollout.run_wave"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        fleet = {"n1": "v1"}
        r = Rollout("v2", waves=[["n1"]])
        r.pin(fleet)
        try:
            r.admit(None)
        except BundleRejected:
            findings[4] = self.satisfied(
                items[4],
                "An unsigned or unverified bundle is refused admission, so no manual path reaches the fleet.",
                *self._evidence("component.py::Rollout.admit"))
        try:
            r.pin({"n1": "v1"})
        except RuntimeError:
            findings[2] = self.satisfied(
                items[2],
                "The rollback target cannot be repointed once pinned, so a rollout cannot redefine what "
                "'previous' means mid-flight.",
                *self._evidence("component.py::Rollout.pin"))
        unpinned = Rollout("v2", waves=[["n1"]])
        unpinned.admit({"verified": True})
        try:
            unpinned.run_wave(healthy=True)
        except NoRollbackTarget:
            findings[1] = self.satisfied(
                items[1],
                "No wave may start without a pinned rollback target; the escape hatch exists before the "
                "risk is taken.",
                *self._evidence("component.py::Rollout.run_wave"))
        return findings

COMPONENT = OtaLifecycleRollbackComponent
