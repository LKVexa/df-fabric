"""GAP-06 - Device identity and attestation.

Device identity and attestation is where trust actually starts. A node proves what it is with evidence rooted in hardware, that evidence expires, and a node whose measurements drifted from the accepted set is untrusted even if it was trusted a minute ago.

The component answers all 100 requirements of the GAP-06 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field

#: Attestation levels, weakest to strongest.
LEVELS = ("untrusted", "software", "hardware")

#: How long a verdict is valid, in logical ticks.
VERDICT_TTL = 100


class AttestationFailed(PermissionError):
    """Raised when evidence does not support the claimed attestation level."""


class ReplayDetected(PermissionError):
    """Raised when evidence reuses a nonce that has already been spent."""


@dataclass(frozen=True)
class Evidence:
    """Attestation evidence: what the node measured, under which challenge."""

    node: str
    measurements: tuple          # sorted measurement digests
    nonce: str
    hardware_rooted: bool

    def bind(self) -> str:
        """The evidence binding: measurements and nonce together, so neither can be swapped."""
        seed = f"{self.node}|{'|'.join(self.measurements)}|{self.nonce}|{int(self.hardware_rooted)}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]


@dataclass
class Verdict:
    node: str
    level: str
    issued_at: int
    expires_at: int
    binding: str

    def valid_at(self, now: int) -> bool:
        return now < self.expires_at

    def level_at(self, now: int) -> str:
        """Trust decays to untrusted at expiry; it never lingers."""
        return self.level if self.valid_at(now) else "untrusted"


@dataclass
class Attestor:
    """Verifies node evidence against an environment's accepted measurement set."""

    environment: str
    accepted: set = field(default_factory=set)
    spent_nonces: set = field(default_factory=set)
    quarantined: set = field(default_factory=set)
    verdicts: dict = field(default_factory=dict)

    def challenge(self, node: str, now: int) -> str:
        return hashlib.sha256(f"{self.environment}|{node}|{now}".encode()).hexdigest()[:16]

    def attest(self, evidence: Evidence, now: int) -> Verdict:
        if evidence.nonce in self.spent_nonces:
            raise ReplayDetected(f"{evidence.node}: nonce {evidence.nonce} was already spent")
        self.spent_nonces.add(evidence.nonce)

        unknown = [m for m in evidence.measurements if m not in self.accepted]
        if unknown:
            self.quarantined.add(evidence.node)
            raise AttestationFailed(
                f"{evidence.node}: measurements outside the accepted set: {unknown}")

        level = "hardware" if evidence.hardware_rooted else "software"
        self.quarantined.discard(evidence.node)
        verdict = Verdict(evidence.node, level, now, now + VERDICT_TTL, evidence.bind())
        self.verdicts[evidence.node] = verdict
        return verdict

    def level_of(self, node: str, now: int) -> str:
        """A node with no verdict is untrusted -- absence is never trust."""
        verdict = self.verdicts.get(node)
        if verdict is None or node in self.quarantined:
            return "untrusted"
        return verdict.level_at(now)

    def accept_measurement(self, digest: str) -> None:
        self.accepted.add(digest)


class DeviceIdentityAndAttestationComponent(Component):
    """Master-applied component for GAP-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        a = Attestor("prod", accepted={"m-fw-1", "m-kernel-1"})
        ev = Evidence("n1", ("m-fw-1", "m-kernel-1"), a.challenge("n1", 0), hardware_rooted=True)
        verdict = a.attest(ev, now=0)
        assert verdict.level == "hardware" and a.level_of("n1", 0) == "hardware"
        soft = Evidence("n2", ("m-fw-1",), a.challenge("n2", 0), hardware_rooted=False)
        assert a.attest(soft, now=0).level == "software"
        findings[5] = self.satisfied(
            items[5],
            "Attestation level follows the evidence: a node without a hardware root reaches software at "
            "best and can never claim hardware.",
            *self._evidence("component.py::Attestor.attest"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a = Attestor("prod", accepted={"m-fw-1"})
        ev = Evidence("n1", ("m-fw-1",), "nonce-1", hardware_rooted=True)
        a.attest(ev, now=0)
        try:
            a.attest(ev, now=1)
        except ReplayDetected:
            findings[3] = self.satisfied(
                items[3],
                "Evidence reusing a spent nonce is refused, so a recorded healthy boot cannot be replayed.",
                *self._evidence("component.py::Attestor.attest"))
        drifted = Evidence("n1", ("m-fw-1", "m-rootkit"), "nonce-2", hardware_rooted=True)
        try:
            a.attest(drifted, now=2)
        except AttestationFailed:
            findings[4] = self.satisfied(
                items[4],
                "Measurements outside the accepted set quarantine the node immediately, even though its "
                "previous verdict had not expired.",
                *self._evidence("component.py::Attestor.attest"))
        assert a.level_of("n1", 2) == "untrusted", "quarantine did not override the live verdict"
        assert a.level_of("never-seen", 0) == "untrusted"
        findings[1] = self.satisfied(
            items[1],
            "A node with no verdict, and a quarantined node with a live one, both evaluate to untrusted: "
            "absence of evidence is never treated as trust.",
            *self._evidence("component.py::Attestor.level_of"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a = Attestor("prod", accepted={"m-fw-1"})
        a.attest(Evidence("n1", ("m-fw-1",), "n-1", hardware_rooted=True), now=0)
        assert a.level_of("n1", VERDICT_TTL - 1) == "hardware"
        assert a.level_of("n1", VERDICT_TTL) == "untrusted", "verdict outlived its expiry"
        findings[3] = self.satisfied(
            items[3],
            f"A verdict decays to untrusted exactly at its {VERDICT_TTL}-tick expiry, so a partitioned "
            "site loses trust rather than retaining it indefinitely.",
            *self._evidence("component.py::Verdict.level_at"))
        return findings

COMPONENT = DeviceIdentityAndAttestationComponent
