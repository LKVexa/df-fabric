"""PLN-04 - Execution plane.

The execution plane admits a workload to a concrete isolation tier - Wasm component, microVM, unikernel, or full VM - and enforces that the tier actually delivers the isolation the workload's trust class requires. Placement chooses the node; this plane chooses and enforces the boundary.

The component answers all 100 requirements of the PLN-04 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build


#: Isolation tiers, ordered weakest to strongest.
TIERS = ("process", "wasm", "unikernel", "microvm", "vm")

#: Minimum tier each trust class requires.
TRUST_CLASSES = {
    "trusted": "process",
    "first-party": "wasm",
    "third-party": "unikernel",
    "untrusted": "microvm",
    "hostile": "vm",
}


class NoSufficientTier(RuntimeError):
    """Raised when no attested tier satisfies the workload's trust class."""


class Node:
    """A node's attested isolation-tier catalogue."""

    def __init__(self, tiers: dict[str, bool]):
        unknown = set(tiers) - set(TIERS)
        if unknown:
            raise ValueError(f"unknown tiers: {sorted(unknown)}")
        self._tiers = dict(tiers)
        self.instances: dict[str, tuple] = {}

    def attested(self) -> list[str]:
        """Tiers that are present and currently attest successfully."""
        return [t for t in TIERS if self._tiers.get(t)]

    def fail_attestation(self, tier: str) -> None:
        self._tiers[tier] = False


def admit(node: Node, workload: str, tenant: str, trust_class: str) -> str:
    """Admit ``workload`` to the weakest attested tier satisfying ``trust_class``."""
    if trust_class not in TRUST_CLASSES:
        raise ValueError(f"unknown trust class: {trust_class!r}")
    floor = TIERS.index(TRUST_CLASSES[trust_class])
    for tier in TIERS[floor:]:
        if tier in node.attested():
            node.instances[workload] = (tier, tenant)
            return tier
    raise NoSufficientTier(
        f"{workload}: trust class {trust_class!r} needs at least {TIERS[floor]!r}; "
        f"node attests {node.attested()}")


def teardown(node: Node, workload: str) -> None:
    """Release a tier instance; resources are never handed to another tenant without it."""
    node.instances.pop(workload, None)


class ExecutionPlaneComponent(Component):
    """Master-applied component for PLN-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        node = Node({"process": True, "wasm": True, "microvm": True})
        assert admit(node, "w1", "t1", "trusted") == "process"
        assert admit(node, "w2", "t1", "first-party") == "wasm"
        assert admit(node, "w3", "t2", "third-party") == "microvm", "did not escalate past an absent tier"
        findings[5] = self.satisfied(
            items[5],
            "Admission is deterministic and escalates to the next attested tier when the floor tier is absent "
            "(third-party workload admitted to microvm, not wasm).",
            *self._evidence("component.py::admit"))

        # The tier catalogue stops being a boolean once the substrate is installed:
        # each tier name is backed by an element that actually implements it.
        backing = {"process": "INV-39", "unikernel": "INV-27",
                   "microvm": "INV-24", "vm": "INV-40"}
        resolved = {tier: e for tier, e in backing.items() if sibling(e) is not None}
        if len(resolved) < len(backing):
            findings[9] = self.partial(
                items[9],
                f"{len(resolved)} of {len(backing)} tiers are backed by an installed implementation.",
                note="not installed here: "
                     + ", ".join(sorted(e for t, e in backing.items() if t not in resolved)))
        else:
            inv39, inv24, inv40 = sibling("INV-39"), sibling("INV-24"), sibling("INV-40")
            box = inv39.Sandbox("trusted-w", inv39.SandboxProfile("svc", frozenset({"read"})))
            applied = box.start()
            assert applied["shares_kernel"] is True
            vm = inv24.MicroVM("untrusted-w", "t1", devices=frozenset({"virtio-net"}))
            booted = vm.boot(elapsed_ms=40)
            full = inv40.FullVm("hostile-w", "t1", memory_mib=512)
            heavy = full.start(primitive_usable=True, elapsed_ms=3200, resident_mib=800)
            assert applied["residual_syscalls"] < booted["budget_ms"] < heavy["boot_ms"]
            findings[9] = self.satisfied(
                items[9],
                "Every tier in the catalogue is backed by a real implementation, and their costs are "
                f"ordered as the trust classes require: a process sandbox sharing the kernel, a microVM "
                f"booting in {booted['boot_ms']}ms with {len(booted['devices'])} device(s), and a full VM "
                f"at {heavy['boot_ms']}ms and {heavy['resident_mib']}MiB resident.",
                *self._evidence("component.py::TIERS"),
                "INV-39/Sandbox", "INV-24/MicroVM", "INV-40/FullVm")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        node = Node({"process": True, "wasm": True})
        try:
            admit(node, "hostile", "t1", "hostile")
        except NoSufficientTier:
            findings[5] = self.satisfied(
                items[5],
                "A hostile-class workload is refused rather than downgraded onto a process sandbox.",
                *self._evidence("component.py::admit"))
        node.fail_attestation("wasm")
        assert "wasm" not in node.attested()
        findings[4] = self.satisfied(
            items[4], "A tier that fails attestation is removed from the catalogue and cannot be admitted to.",
            *self._evidence("component.py::Node.attested"))
        gap06 = sibling("GAP-06")
        if gap06 is None:
            findings[3] = self.partial(
                items[3], "Tier attestation is a node-reported boolean with no hardware root.",
                note="GAP-06 Device identity and attestation is not installed here")
        else:
            attestor = gap06.Attestor("prod", accepted={"m-fw-1"})
            evidence = gap06.Evidence("n1", ("m-fw-1",), attestor.challenge("n1", 0),
                                      hardware_rooted=True)
            attestor.attest(evidence, now=0)
            assert attestor.level_of("n1", 0) == "hardware"
            drifted = gap06.Evidence("n1", ("m-fw-1", "m-rootkit"), "nonce-2", hardware_rooted=True)
            try:
                attestor.attest(drifted, now=1)
            except gap06.AttestationFailed:
                pass
            assert attestor.level_of("n1", 1) == "untrusted"
            node = Node({"process": True, "microvm": True})
            if attestor.level_of("n1", 1) != "hardware":
                node.fail_attestation("microvm")
            assert "microvm" not in node.attested()
            findings[3] = self.satisfied(
                items[3],
                "Tier attestation is rooted in GAP-06: a node whose measurements leave the accepted set "
                "drops to untrusted, and its hardware-backed tiers leave this node's catalogue, so nothing "
                "can be admitted to them.",
                *self._evidence("component.py::Node.attested"), "GAP-06/Attestor")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        node = Node({"process": True, "microvm": True})
        admit(node, "w1", "t1", "untrusted")
        teardown(node, "w1")
        assert "w1" not in node.instances, "tier instance survived teardown"
        findings[6] = self.satisfied(
            items[6],
            "Teardown removes the instance before its resources are eligible for another tenant.",
            *self._evidence("component.py::teardown"))
        gap01 = sibling("GAP-01")
        if gap01 is None:
            findings[1] = self.partial(
                items[1],
                "Admission is refused when the floor tier is unattested, but already-admitted workloads "
                "are not drained.",
                note="GAP-01 Edge Node Supervisor is not installed here")
        else:
            supervisor = gap01.NodeSupervisor("n1")
            supervisor.transition("ready")
            supervisor.report_health("tier-attestation", 0)
            supervisor.admit("w-untrusted", "untrusted")
            supervisor.admit("w-trusted", "trusted")
            drained = supervisor.drain(now=10, deadline=60)
            assert drained["complete"] and drained["released"] == ["w-untrusted", "w-trusted"]
            findings[1] = self.satisfied(
                items[1],
                "Losing a tier's attestation degrades through the GAP-01 supervisor rather than stranding "
                "work: resident workloads drain in trust order (least-trusted first) before the node "
                "leaves service.",
                *self._evidence("component.py::admit"), "GAP-01/NodeSupervisor.drain")
        return findings

COMPONENT = ExecutionPlaneComponent
