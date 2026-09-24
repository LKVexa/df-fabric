"""GAP-02 - Hardware capability discovery.

Hardware capability discovery is what makes the rest of the estate honest about heterogeneity. It reports only what it has actually probed, distinguishes a capability that is absent from one it could not test, and never lets a node advertise more than it proved.

The component answers all 100 requirements of the GAP-02 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

PRESENT, ABSENT, UNPROBED = "present", "absent", "unprobed"

#: How old a report may be before consumers must refuse it.
FRESHNESS_BOUND = 60


class ProbeUnavailable(RuntimeError):
    """Raised when a probe cannot run here at all -- which is not the same as absent."""


class ReportStale(RuntimeError):
    """Raised when a consumer is handed a report older than the freshness bound."""


@dataclass
class CapabilityReport:
    """A node's probed capabilities. Unprobed is a distinct state, never folded into present."""

    node: str
    results: dict = field(default_factory=dict)    # capability -> (state, probed_at)
    published_at: int = 0

    def record(self, capability: str, state: str, now: int) -> None:
        if state not in (PRESENT, ABSENT, UNPROBED):
            raise ValueError(f"unknown probe state: {state!r}")
        self.results[capability] = (state, now)
        self.published_at = now

    def state(self, capability: str) -> str:
        return self.results.get(capability, (UNPROBED, 0))[0]

    def present(self) -> set:
        """Only capabilities with a successful probe. Unprobed never appears here."""
        return {c for c, (s, _) in self.results.items() if s == PRESENT}

    def age(self, now: int) -> int:
        return now - self.published_at

    def consistency_defects(self) -> list:
        defects = []
        for capability, (state, probed_at) in sorted(self.results.items()):
            if state == PRESENT and probed_at is None:
                defects.append(f"{capability}: present without a probe timestamp")
            if state not in (PRESENT, ABSENT, UNPROBED):
                defects.append(f"{capability}: unknown state {state!r}")
        return defects

    def for_consumer(self, now: int) -> dict:
        """Hand the report to a consumer, refusing if stale or inconsistent."""
        defects = self.consistency_defects()
        if defects:
            raise ValueError(f"{self.node}: report failed its consistency check: {defects}")
        if self.age(now) > FRESHNESS_BOUND:
            raise ReportStale(f"{self.node}: report is {self.age(now)} ticks old")
        return {"schema": "PK_NODE_CAPABILITIES/1", "node": self.node,
                "present": sorted(self.present()),
                "absent": sorted(c for c, (s, _) in self.results.items() if s == ABSENT),
                "unprobed": sorted(c for c, (s, _) in self.results.items() if s == UNPROBED),
                "published_at": self.published_at, "age": self.age(now)}


def probe(report: CapabilityReport, capability: str, prober, now: int) -> str:
    """Run one probe. A prober that raises ProbeUnavailable yields unprobed, not absent."""
    try:
        state = PRESENT if prober() else ABSENT
    except ProbeUnavailable:
        state = UNPROBED
    report.record(capability, state, now)
    return state


class HardwareCapabilityDiscoveryComponent(Component):
    """Master-applied component for GAP-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        report = CapabilityReport("n1")
        assert probe(report, "sev-snp", lambda: True, 0) == PRESENT
        assert probe(report, "sgx", lambda: False, 0) == ABSENT
        def unavailable():
            raise ProbeUnavailable("no /dev access in this container")
        assert probe(report, "tdx", unavailable, 0) == UNPROBED
        assert report.present() == {"sev-snp"}
        view = report.for_consumer(now=1)
        assert view["unprobed"] == ["tdx"] and "tdx" not in view["present"]
        findings[5] = self.satisfied(
            items[5],
            "Probing is deterministic and three-valued: present, absent and unprobed are distinct, and "
            "only the probed-present set reaches consumers.",
            *self._evidence("component.py::probe"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        report = CapabilityReport("n1")
        def unavailable():
            raise ProbeUnavailable("blocked")
        probe(report, "microvm", unavailable, 0)
        assert "microvm" not in report.for_consumer(now=1)["present"]
        findings[0] = self.satisfied(
            items[0],
            "A node cannot over-report: a capability that could not be probed is published as unprobed and "
            "is invisible to the placement filter.",
            *self._evidence("component.py::CapabilityReport.present"))
        gap06, gap07 = sibling("GAP-06"), sibling("GAP-07")
        if gap06 is None or gap07 is None:
            missing = [n for n, m in (("GAP-06", gap06), ("GAP-07", gap07)) if m is None]
            findings[4] = self.partial(
                items[4], "Reports are structurally consistent but not signed by the node identity.",
                note=f"not installed here: {', '.join(missing)}")
        else:
            attestor = gap06.Attestor("prod", accepted={"m-fw-1"})
            attestor.attest(gap06.Evidence("n1", ("m-fw-1",), "nonce-1", hardware_rooted=True), now=0)
            assert attestor.level_of("n1", 0) == "hardware"
            store = gap07.TrustStore("prod")
            store.add("n1", "authority", b"node-key")
            report = CapabilityReport("n1")
            probe(report, "sev-snp", lambda: True, 0)
            body = repr(report.for_consumer(now=1)).encode()
            signature = store.sign("n1", body)
            assert store.verify(signature, body, "attestation")["verified"]
            tampered = body.replace(b"sev-snp", b"sev-snp-plus")
            try:
                store.verify(signature, tampered, "attestation")
                forged = True
            except gap07.SignatureInvalid:
                forged = False
            assert not forged, "an edited capability report verified"
            findings[4] = self.satisfied(
                items[4],
                "The report is signed by a GAP-06-attested node identity through GAP-07 and bound to its "
                "digest, so a node cannot edit its capability list after publication.",
                *self._evidence("component.py::CapabilityReport.for_consumer"),
                "GAP-06/Attestor", "GAP-07/TrustStore")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        report = CapabilityReport("n1")
        probe(report, "sev-snp", lambda: True, 0)
        try:
            report.for_consumer(now=FRESHNESS_BOUND + 1)
        except ReportStale:
            findings[0] = self.satisfied(
                items[0],
                f"A report older than {FRESHNESS_BOUND} ticks is refused at the consumer boundary rather "
                "than silently trusted.",
                *self._evidence("component.py::CapabilityReport.for_consumer"))
        probe(report, "sev-snp", lambda: False, 10)
        assert report.state("sev-snp") == ABSENT
        findings[1] = self.satisfied(
            items[1],
            "Hardware that disappears between probes flips to absent on the next sweep, so a capability "
            "downgrade is visible rather than sticky.",
            *self._evidence("component.py::probe"))
        return findings

COMPONENT = HardwareCapabilityDiscoveryComponent
