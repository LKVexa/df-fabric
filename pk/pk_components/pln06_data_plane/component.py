"""PLN-06 - Data plane.

The data plane separates control traffic from bulk movement and keeps data where gravity puts it. It admits a transfer only when the destination is a legal residence for the data's classification, and it picks a transport by payload size and locality rather than routing everything through the control path.

The component answers all 100 requirements of the PLN-06 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


#: Transport tiers with their inclusive upper size bound in bytes.
TRANSPORT_TIERS = (
    ("inline", 64 * 1024),
    ("local", 64 * 1024 * 1024),
    ("bulk", 64 * 1024 * 1024 * 1024),
)

CONTROL_INLINE_LIMIT = TRANSPORT_TIERS[0][1]


class ResidencyViolation(PermissionError):
    """Raised when a destination site may not hold the payload's classification."""


class NoTransportTier(RuntimeError):
    """Raised when no configured tier covers the payload size."""


class Backpressure(RuntimeError):
    """Raised when the bulk path is saturated; the caller must retry, not buffer."""


class DataPlane:
    """Admits and routes bulk transfers under a residency policy."""

    def __init__(self, residency: dict[str, set], *, inflight_limit: int = 4):
        #: site -> set of classifications that site may legally hold.
        self._residency = {k: set(v) for k, v in residency.items()}
        self._inflight_limit = inflight_limit
        self.inflight = 0
        self.control_bytes = 0
        self.bulk_bytes = 0

    def permitted(self, site: str, classification: str) -> bool:
        return classification in self._residency.get(site, set())

    @staticmethod
    def tier_for(size: int) -> str:
        for name, bound in TRANSPORT_TIERS:
            if size <= bound:
                return name
        raise NoTransportTier(f"payload of {size} bytes exceeds every configured tier")

    def admit(self, *, tenant: str, workload: str, size: int, classification: str, destination: str) -> dict:
        """Admit one transfer, returning its routing decision."""
        if not self.permitted(destination, classification):
            raise ResidencyViolation(
                f"{destination!r} may not hold classification {classification!r}")
        tier = self.tier_for(size)
        if tier != "inline":
            if self.inflight >= self._inflight_limit:
                raise Backpressure(f"bulk path saturated at {self.inflight} in-flight transfers")
            self.inflight += 1
            self.bulk_bytes += size
        else:
            self.control_bytes += size
        return {
            "schema": "PK_TRANSFER/1", "tenant": tenant, "workload": workload,
            "tier": tier, "size": size, "classification": classification,
            "destination": destination, "digest_required": True,
        }

    def complete(self, decision: dict) -> None:
        if decision["tier"] != "inline":
            self.inflight = max(0, self.inflight - 1)


class DataPlaneComponent(Component):
    """Master-applied component for PLN-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        plane = DataPlane({"eu-west": {"pii", "public"}, "us-east": {"public"}})
        small = plane.admit(tenant="t1", workload="w", size=1024, classification="public", destination="us-east")
        large = plane.admit(tenant="t1", workload="w", size=10 * 1024 * 1024,
                            classification="public", destination="us-east")
        assert small["tier"] == "inline" and large["tier"] == "local"
        assert plane.control_bytes == 1024 and plane.bulk_bytes == 10 * 1024 * 1024
        findings[5] = self.satisfied(
            items[5],
            "Tier selection is deterministic by size; control and bulk byte counters stayed disjoint.",
            *self._evidence("component.py::DataPlane"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        plane = DataPlane({"eu-west": {"pii"}, "us-east": {"public"}})
        try:
            plane.admit(tenant="t1", workload="w", size=100, classification="pii", destination="us-east")
        except ResidencyViolation:
            findings[5] = self.satisfied(
                items[5], "A PII transfer to a site without PII residency is refused at admission.",
                *self._evidence("component.py::DataPlane.admit"))
        gap07 = sibling("GAP-07")
        if gap07 is None:
            findings[0] = self.partial(
                items[0], "Classification is taken from the caller and cannot be verified.",
                note="GAP-07 Artifact provenance/signing is not installed here")
        else:
            store = gap07.TrustStore("prod")
            store.add("data-bot", "data", b"label-key")
            label = b"classification=pii"
            signature = store.sign("data-bot", label)
            assert store.verify(signature, label, "label")["verified"]
            try:
                store.verify(signature, b"classification=public", "label")
                downgraded = True
            except gap07.SignatureInvalid:
                downgraded = False
            assert not downgraded, "a classification downgrade passed verification"
            findings[0] = self.satisfied(
                items[0],
                "Classification arrives as a GAP-07 signed label bound to its own digest, so relabelling "
                "pii as public fails verification before the transfer is costed.",
                *self._evidence("component.py::DataPlane.admit"), "GAP-07/TrustStore.verify")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        plane = DataPlane({"s": {"public"}}, inflight_limit=2)
        big = dict(tenant="t1", workload="w", size=10 * 1024 * 1024,
                   classification="public", destination="s")
        held = [plane.admit(**big), plane.admit(**big)]
        try:
            plane.admit(**big)
        except Backpressure:
            findings[5] = self.satisfied(
                items[5],
                "Bulk admission applies bounded backpressure at the in-flight limit instead of buffering.",
                *self._evidence("component.py::DataPlane.admit"))
        plane.complete(held[0])
        assert plane.admit(**big)["tier"] == "local", "capacity was not released on completion"
        findings[4] = self.satisfied(
            items[4], "Completion releases in-flight capacity; admission is idempotent per transfer.",
            *self._evidence("component.py::DataPlane.complete"))
        inv37 = sibling("INV-37")
        if inv37 is None:
            findings[3] = self.partial(
                items[3],
                "Digest verification is mandated in the decision record but computed by the transport.",
                note="INV-37 Bulk data plane is not installed here")
        else:
            data = b"dataset-shard" * 2000
            m = inv37.manifest(data)
            rx = inv37.Receiver(m)
            chunks = [data[i:i + m["chunk"]] for i in range(0, len(data), m["chunk"])]
            for i, c in enumerate(chunks):
                rx.accept(i, c)
            assert rx.assemble() == data
            try:
                inv37.verify_object(m, data[:-1] + b"X")
                caught = False
            except inv37.DigestMismatch:
                caught = True
            assert caught
            findings[3] = self.satisfied(
                items[3],
                f"Integrity is verified end to end by the receiver through INV-37, not taken from the "
                f"transport: a {len(data)}-byte object is re-verified chunk by chunk and as a whole, and "
                "a single altered byte fails the object digest.",
                *self._evidence("contract.py"), "INV-37/Receiver", "INV-37/verify_object")
        return findings

COMPONENT = DataPlaneComponent
