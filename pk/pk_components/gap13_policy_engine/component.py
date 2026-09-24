"""GAP-13 - Policy engine.

The policy engine is where the estate's rules are evaluated rather than scattered. Decisions default to deny, the most specific matching rule wins with deterministic tie-breaking, and every verdict carries the rule that produced it -- so an operator can always answer why.

The component answers all 100 requirements of the GAP-13 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Cached policy older than this must be reported stale to the caller.
BUNDLE_STALENESS_BOUND = 300


class BundleRejected(PermissionError):
    """Raised when a policy bundle fails verification and is not loaded."""


class ScopeEscalation(PermissionError):
    """Raised when a tenant rule tries to widen estate-level authority."""


@dataclass(frozen=True)
class Rule:
    """One policy rule. ``match`` is an attribute subset; more attributes means more specific."""

    name: str
    effect: str                  # "allow" | "deny"
    match: tuple                 # ((attribute, value), ...) sorted
    scope: str = "estate"        # "estate" | "tenant"

    def __post_init__(self):
        if self.effect not in ("allow", "deny"):
            raise ValueError(f"unknown effect: {self.effect!r}")

    @property
    def specificity(self) -> int:
        return len(self.match)

    def matches(self, request: dict) -> bool:
        return all(request.get(k) == v for k, v in self.match)


@dataclass
class PolicyEngine:
    """Deny-by-default, most-specific-wins, always-explainable policy evaluation."""

    environment: str
    version: str = "none"
    rules: list = field(default_factory=list)
    loaded_at: int = 0

    def load(self, rules: list, version: str, verification: dict | None, now: int = 0) -> str:
        if not verification or not verification.get("verified"):
            raise BundleRejected(f"{self.environment}: policy bundle {version} is not verified")
        for rule in rules:
            if rule.scope == "tenant" and rule.effect == "allow":
                estate_denies = [r for r in rules
                                 if r.scope == "estate" and r.effect == "deny" and
                                 set(r.match) <= set(rule.match)]
                if estate_denies:
                    raise ScopeEscalation(
                        f"{rule.name}: tenant rule would widen estate deny "
                        f"{estate_denies[0].name}")
        self.rules = list(rules)
        self.version = version
        self.loaded_at = now
        return version

    def evaluate(self, request: dict, now: int = 0) -> dict:
        matched = [r for r in self.rules if r.matches(request)]
        stale = now - self.loaded_at > BUNDLE_STALENESS_BOUND
        if not matched:
            return {"schema": "PK_POLICY_VERDICT/1", "effect": "deny",
                    "rule": None, "reason": "no matching rule; policy denies by default",
                    "version": self.version, "stale": stale, "tie_break": False,
                    "considered": []}
        # Most specific wins; deny beats allow at equal specificity; then rule name.
        ordered = sorted(matched,
                         key=lambda r: (-r.specificity, r.effect != "deny", r.name))
        winner = ordered[0]
        peers = [r for r in matched
                 if r.specificity == winner.specificity and r.effect != winner.effect]
        return {"schema": "PK_POLICY_VERDICT/1", "effect": winner.effect,
                "rule": winner.name,
                "reason": f"matched {winner.specificity} attribute(s) via {winner.name}",
                "version": self.version, "stale": stale,
                "tie_break": bool(peers),
                "considered": [r.name for r in ordered]}


class PolicyEngineComponent(Component):
    """Master-applied component for GAP-13."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        engine = PolicyEngine("prod")
        engine.load([
            Rule("broad-allow", "allow", (("action", "read"),)),
            Rule("narrow-deny", "deny", (("action", "read"), ("classification", "pii"))),
        ], "v1", {"verified": True}, now=0)
        general = engine.evaluate({"action": "read", "classification": "public"})
        specific = engine.evaluate({"action": "read", "classification": "pii"})
        assert general["effect"] == "allow" and specific["effect"] == "deny"
        assert specific["rule"] == "narrow-deny"
        repeat = engine.evaluate({"action": "read", "classification": "pii"})
        assert repeat == specific, "evaluation is not deterministic"
        findings[5] = self.satisfied(
            items[5],
            "Evaluation is deterministic and most-specific-wins: a two-attribute deny overrides a "
            "one-attribute allow, and repeated evaluation is byte-identical.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        engine = PolicyEngine("prod")
        verdict = engine.evaluate({"action": "anything"})
        assert verdict["effect"] == "deny" and verdict["rule"] is None
        findings[1] = self.satisfied(
            items[1],
            "An empty or non-matching policy denies: least privilege is the default state, not a "
            "configuration choice.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        try:
            engine.load([Rule("r", "allow", (("action", "read"),))], "v1", None)
        except BundleRejected:
            findings[4] = self.satisfied(
                items[4],
                "An unverified bundle is never loaded, so a permissive rule cannot enter without a valid "
                "signature from GAP-07.",
                *self._evidence("component.py::PolicyEngine.load"))
        try:
            engine.load([
                Rule("estate-deny", "deny", (("action", "write"),), scope="estate"),
                Rule("tenant-allow", "allow", (("action", "write"), ("tenant", "t1")), scope="tenant"),
            ], "v2", {"verified": True})
        except ScopeEscalation:
            findings[5] = self.satisfied(
                items[5],
                "A tenant rule that would widen an estate-level deny is refused at load time, so tenant "
                "policy can only narrow.",
                *self._evidence("component.py::PolicyEngine.load"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        engine = PolicyEngine("prod")
        engine.load([
            Rule("a-allow", "allow", (("action", "read"),)),
            Rule("b-deny", "deny", (("action", "read"),)),
        ], "v1", {"verified": True}, now=0)
        verdict = engine.evaluate({"action": "read"})
        assert verdict["effect"] == "deny" and verdict["tie_break"]
        assert verdict["considered"] == ["b-deny", "a-allow"]
        findings[7] = self.satisfied(
            items[7],
            "Equally specific rules resolve deny-first, the tie-break is flagged, and every considered rule "
            "is listed -- so 'why was this denied' has a complete answer.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        stale = engine.evaluate({"action": "read"}, now=BUNDLE_STALENESS_BOUND + 1)
        assert stale["stale"] and stale["version"] == "v1"
        findings[3] = self.satisfied(
            items[3],
            "Verdicts carry the policy version and their own staleness, so a decision taken on a cached "
            "bundle at a disconnected site is identifiable afterwards.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        return findings

COMPONENT = PolicyEngineComponent
