"""GAP-07 - Artifact provenance/signing.

Artifact provenance and signing is the estate's supply-chain gate. Nothing executable or policy-bearing is consumed without a signature chaining to a trusted root, and the signature covers the artifact's digest, so swapping the bytes under a valid signature fails.

The component answers all 100 requirements of the GAP-07 checklist.  Bands
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

#: Which signer roles may sign which artifact kinds.
ROLE_FOR_KIND = {
    "code": "release", "policy": "policy", "grant": "authority",
    "label": "data", "attestation": "authority", "bundle": "release",
}


class Unsigned(PermissionError):
    """Raised when an artifact that requires a signature has none."""


class SignatureInvalid(PermissionError):
    """Raised when a signature does not verify against the artifact's digest."""


class SignerUntrusted(PermissionError):
    """Raised when the signer is absent, revoked, or holds the wrong role."""


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Signature:
    """A signature over an artifact's DIGEST, not over its name or metadata."""

    signer: str
    digest: str
    mac: str


@dataclass
class TrustStore:
    """Accepted signers and their roles, with revocation."""

    environment: str
    #: signer -> (role, secret)
    signers: dict = field(default_factory=dict)
    revoked: set = field(default_factory=set)
    updated_at: int = 0

    def add(self, signer: str, role: str, secret: bytes, now: int = 0) -> None:
        self.signers[signer] = (role, secret)
        self.updated_at = now

    def revoke(self, signer: str, now: int = 0) -> None:
        self.revoked.add(signer)
        self.updated_at = now

    def role_of(self, signer: str) -> str:
        if signer not in self.signers or signer in self.revoked:
            raise SignerUntrusted(f"{signer} is not a trusted signer in {self.environment}")
        return self.signers[signer][0]

    def _secret(self, signer: str) -> bytes:
        self.role_of(signer)
        return self.signers[signer][1]

    def sign(self, signer: str, payload: bytes) -> Signature:
        d = digest(payload)
        mac = hmac.new(self._secret(signer), d.encode(), hashlib.sha256).hexdigest()
        return Signature(signer, d, mac)

    def verify(self, signature: Signature | None, payload: bytes, kind: str) -> dict:
        """Verify an artifact. Every failure mode is a distinct, named refusal."""
        if signature is None:
            raise Unsigned(f"{kind} artifacts require a signature")
        role = self.role_of(signature.signer)          # raises if absent or revoked
        required = ROLE_FOR_KIND.get(kind)
        if required and role != required:
            raise SignerUntrusted(
                f"{signature.signer} holds role {role!r}; {kind!r} requires {required!r}")
        actual = digest(payload)
        if actual != signature.digest:
            raise SignatureInvalid(
                f"digest mismatch: signature covers {signature.digest[:12]}, bytes are {actual[:12]}")
        expected = hmac.new(self._secret(signature.signer), actual.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature.mac):
            raise SignatureInvalid("signature does not verify")
        return {"schema": "PK_VERIFICATION/1", "kind": kind, "signer": signature.signer,
                "role": role, "digest": actual, "verified": True}


def provenance(chain: list) -> dict:
    """Record the chain from source to deployed artifact, each link digest-bound."""
    links = []
    previous = None
    for step, payload in chain:
        d = digest(payload)
        links.append({"step": step, "digest": d, "previous": previous})
        previous = d
    return {"schema": "PK_PROVENANCE/1", "links": links, "head": previous}


class ArtifactProvenanceSigningComponent(Component):
    """Master-applied component for GAP-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        store = TrustStore("prod")
        store.add("release-bot", "release", b"k1")
        payload = b"executable-bytes"
        sig = store.sign("release-bot", payload)
        result = store.verify(sig, payload, "code")
        assert result["verified"] and result["digest"] == digest(payload)
        chain = provenance([("source", b"src"), ("build", b"obj"), ("package", payload)])
        assert chain["head"] == digest(payload) and chain["links"][1]["previous"] == digest(b"src")
        findings[5] = self.satisfied(
            items[5],
            f"Signing and verification are digest-bound end to end; the provenance chain links "
            f"{len(chain['links'])} steps, each carrying its predecessor's digest.",
            *self._evidence("component.py::TrustStore.verify", "component.py::provenance"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        store = TrustStore("prod")
        store.add("release-bot", "release", b"k1")
        store.add("data-bot", "data", b"k2")
        payload = b"executable-bytes"
        sig = store.sign("release-bot", payload)

        proven = []
        try:
            store.verify(sig, b"substituted-bytes", "code")
        except SignatureInvalid:
            proven.append("byte substitution")
        try:
            store.verify(None, payload, "code")
        except Unsigned:
            proven.append("signature stripping")
        try:
            store.verify(store.sign("data-bot", payload), payload, "code")
        except SignerUntrusted:
            proven.append("role confusion")
        assert len(proven) == 3, proven
        findings[4] = self.satisfied(
            items[4],
            f"Three supply-chain attacks are refused by construction: {', '.join(proven)}.",
            *self._evidence("component.py::TrustStore.verify"))

        store.revoke("release-bot")
        try:
            store.verify(sig, payload, "code")
        except SignerUntrusted:
            findings[3] = self.satisfied(
                items[3],
                "Revoking a signer immediately refuses artifacts it signed earlier, so revocation is not "
                "limited to future signings.",
                *self._evidence("component.py::TrustStore.role_of"))
        findings[8] = self.partial(
            items[8],
            "Signatures are HMAC-based for a self-contained reference build; asymmetric keys with external "
            "custody and a transparency log are specified and belong with the estate's real KMS.",
            note="requires key custody outside this element's scope")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        store = TrustStore("prod")
        store.add("bot", "policy", b"k")
        good = store.sign("bot", b"policy-bytes")
        for payload, kind, expected in [
            (b"policy-bytes", "policy", None),
            (b"tampered", "policy", SignatureInvalid),
            (b"policy-bytes", "code", SignerUntrusted),
        ]:
            try:
                store.verify(good, payload, kind)
                assert expected is None
            except Exception as exc:
                assert isinstance(exc, expected), f"{kind}: got {type(exc).__name__}"
        findings[0] = self.satisfied(
            items[0],
            "Each declared failure mode raises its own named exception, so a caller cannot conflate a "
            "tampered artifact with an untrusted signer.",
            *self._evidence("component.py::TrustStore.verify"))
        return findings

COMPONENT = ArtifactProvenanceSigningComponent
