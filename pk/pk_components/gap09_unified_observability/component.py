"""GAP-09 - Unified observability.

Unified observability is the estate's evidence layer. Every signal is attributed to the workload and tenant that produced it, signed by the node that reported it, and carries its own staleness -- so a missing signal reads as missing rather than as zero.

The component answers all 100 requirements of the GAP-09 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Beyond this age a value is reported as stale rather than current.
STALENESS_BOUND = 60

#: Sentinel distinguishing "never reported" from the number zero.
ABSENT = None


class ReporterUntrusted(PermissionError):
    """Raised when a submission comes from an unattested or unsigned reporter."""


class Unattributed(ValueError):
    """Raised when a signal lacks tenant, site, or workload attribution."""


class CrossTenantQuery(PermissionError):
    """Raised when a query would return another tenant's signals."""


@dataclass(frozen=True)
class Sample:
    signal: str
    value: float
    tenant: str
    site: str
    workload: str
    at: int


@dataclass
class SignalStore:
    """Tenant-attributed signal storage where absence is a first-class answer."""

    #: (tenant, site, workload, signal) -> Sample
    latest: dict = field(default_factory=dict)
    reporters_silent_after: int = STALENESS_BOUND
    last_submission: dict = field(default_factory=dict)
    rejected: list = field(default_factory=list)

    def submit(self, reporter: str, samples: list, *, attested_level: str, signed: bool, now: int) -> int:
        if attested_level == "untrusted" or not signed:
            self.rejected.append({"reporter": reporter, "reason": "unattested or unsigned", "at": now})
            raise ReporterUntrusted(
                f"{reporter}: submissions require an attested identity and a signature")
        accepted = 0
        for sample in samples:
            if not (sample.tenant and sample.site and sample.workload):
                self.rejected.append({"reporter": reporter, "reason": "unattributed", "at": now})
                raise Unattributed(f"{sample.signal}: tenant, site and workload are all required")
            key = (sample.tenant, sample.site, sample.workload, sample.signal)
            existing = self.latest.get(key)
            # Late and out-of-order arrivals never overwrite a newer sample.
            if existing is None or sample.at >= existing.at:
                self.latest[key] = sample
            accepted += 1
        self.last_submission[reporter] = now
        return accepted

    def read(self, *, caller_tenant: str, tenant: str, site: str, workload: str,
             signal: str, now: int) -> dict:
        if caller_tenant != tenant:
            raise CrossTenantQuery(f"{caller_tenant} may not read signals for {tenant}")
        sample = self.latest.get((tenant, site, workload, signal))
        if sample is None:
            # Absent is not zero.
            return {"schema": "PK_SIGNAL_QUERY/1", "signal": signal, "value": ABSENT,
                    "present": False, "stale": True, "age": None}
        age = now - sample.at
        return {"schema": "PK_SIGNAL_QUERY/1", "signal": signal, "value": sample.value,
                "present": True, "stale": age > STALENESS_BOUND, "age": age}

    def silent_reporters(self, attested: list, now: int) -> list:
        return sorted(r for r in attested
                      if now - self.last_submission.get(r, -10**9) > self.reporters_silent_after)


class UnifiedObservabilityComponent(Component):
    """Master-applied component for GAP-09."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        store = SignalStore()
        s = Sample("cpu", 0.0, "t1", "dub", "w1", at=10)
        store.submit("n1", [s], attested_level="hardware", signed=True, now=10)
        zero = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                          signal="cpu", now=11)
        missing = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                             signal="never", now=11)
        assert zero["value"] == 0.0 and zero["present"]
        assert missing["value"] is ABSENT and not missing["present"]
        findings[5] = self.satisfied(
            items[5],
            "A reported zero and a never-reported signal are distinguishable: the first returns 0.0 with "
            "present=True, the second returns absent with present=False.",
            *self._evidence("component.py::SignalStore.read"))
        late = Sample("cpu", 99.0, "t1", "dub", "w1", at=5)
        store.submit("n1", [late], attested_level="hardware", signed=True, now=12)
        assert store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                          signal="cpu", now=12)["value"] == 0.0
        findings[6] = self.satisfied(
            items[6],
            "A late, out-of-order sample does not overwrite a newer one, so reordering cannot rewrite "
            "history.",
            *self._evidence("component.py::SignalStore.submit"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        store = SignalStore()
        s = Sample("demand", 1.0, "t1", "dub", "w1", at=0)
        try:
            store.submit("rogue", [s], attested_level="untrusted", signed=True, now=0)
        except ReporterUntrusted:
            findings[3] = self.satisfied(
                items[3],
                "An unattested reporter cannot inject signals, closing the forged-demand path that PLN-05 "
                "depends on.",
                *self._evidence("component.py::SignalStore.submit"))
        try:
            store.submit("n1", [s], attested_level="hardware", signed=False, now=0)
        except ReporterUntrusted:
            findings[4] = self.satisfied(
                items[4],
                "An unsigned submission is refused even from an attested node, so signatures are required "
                "per submission rather than per identity.",
                *self._evidence("component.py::SignalStore.submit"))
        store.submit("n1", [s], attested_level="hardware", signed=True, now=0)
        try:
            store.read(caller_tenant="t2", tenant="t1", site="dub", workload="w1",
                       signal="demand", now=1)
        except CrossTenantQuery:
            findings[5] = self.satisfied(
                items[5],
                "A query naming another tenant is refused outright rather than filtered, so scope is "
                "enforced at the boundary.",
                *self._evidence("component.py::SignalStore.read"))
        try:
            store.submit("n1", [Sample("x", 1.0, "t1", "", "w1", at=0)],
                         attested_level="hardware", signed=True, now=0)
        except Unattributed:
            findings[7] = self.satisfied(
                items[7],
                "A signal missing any attribution dimension is refused, so no signal is unaccountable.",
                *self._evidence("component.py::SignalStore.submit"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        store = SignalStore()
        store.submit("n1", [Sample("cpu", 1.0, "t1", "dub", "w1", at=0)],
                     attested_level="hardware", signed=True, now=0)
        fresh = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                           signal="cpu", now=1)
        old = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                         signal="cpu", now=STALENESS_BOUND + 5)
        assert not fresh["stale"] and old["stale"] and old["value"] == 1.0
        findings[8] = self.satisfied(
            items[8],
            "Every read carries its own staleness, so a consumer can tell a current value from one that "
            "stopped being updated an hour ago.",
            *self._evidence("component.py::SignalStore.read"))
        assert store.silent_reporters(["n1", "n2"], now=0) == ["n2"]
        assert store.silent_reporters(["n1"], now=STALENESS_BOUND + 5) == ["n1"]
        findings[0] = self.satisfied(
            items[0],
            "A reporter that goes silent is detected as silent rather than inferred healthy, closing the "
            "signal-suppression path.",
            *self._evidence("component.py::SignalStore.silent_reporters"))
        return findings

COMPONENT = UnifiedObservabilityComponent
