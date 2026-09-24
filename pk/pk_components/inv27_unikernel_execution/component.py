"""INV-27 - Unikernel execution.

Unikernel execution is the single-address-space bet: the application and its kernel are linked into one image with no shell, no second process and no syscall surface to abuse. The isolation argument only holds if the image really is sealed, so this element verifies the seal rather than assuming it.

The component answers all 100 requirements of the INV-27 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Capabilities that contradict the sealed single-address-space model.
DISQUALIFYING = frozenset({"fork", "exec", "dlopen", "ptrace", "shell"})


class SealInvalid(PermissionError):
    """Raised when an image is not genuinely sealed."""


@dataclass(frozen=True)
class UnikernelImage:
    """A unikernel image and the seal it claims."""

    name: str
    toolchain: str
    architecture: str
    declared_syscalls: frozenset      # what the manifest claims
    linked_syscalls: frozenset        # what the binary actually references
    features: frozenset = frozenset() # fork / exec / dlopen / ... if present
    single_address_space: bool = True


def verify_seal(image: UnikernelImage, *, permitted: frozenset, architecture: str) -> dict:
    """Verify the seal against the binary, not against the manifest's word for it."""
    if not image.single_address_space:
        raise SealInvalid(f"{image.name}: image is not single-address-space")
    disqualifying = image.features & DISQUALIFYING
    if disqualifying:
        raise SealInvalid(
            f"{image.name}: image supports {sorted(disqualifying)}, which breaks the seal")
    drift = image.linked_syscalls ^ image.declared_syscalls
    if drift:
        raise SealInvalid(
            f"{image.name}: syscall manifest drifts from the binary: {sorted(drift)}")
    outside = image.linked_syscalls - permitted
    if outside:
        raise SealInvalid(
            f"{image.name}: syscalls outside the environment's permitted set: {sorted(outside)}")
    if image.architecture != architecture:
        raise SealInvalid(
            f"{image.name}: built for {image.architecture}, site runs {architecture}")
    return {"schema": "PK_UNIKERNEL_IMAGE/1", "image": image.name,
            "toolchain": image.toolchain, "sealed": True,
            "syscalls": sorted(image.linked_syscalls),
            "syscall_count": len(image.linked_syscalls)}


@dataclass
class UnikernelInstance:
    name: str
    tenant: str
    seal: dict
    state: str = "running"

    def stop(self) -> str:
        self.state = "stopped"
        return self.state


def run(image: UnikernelImage, *, tenant: str, permitted: frozenset,
        architecture: str) -> UnikernelInstance:
    return UnikernelInstance(image.name, tenant, verify_seal(
        image, permitted=permitted, architecture=architecture))


class UnikernelExecutionComponent(Component):
    """Master-applied component for INV-27."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        syscalls = frozenset({"read", "write", "clock_gettime"})
        image = UnikernelImage("svc", "mirageos", "x86_64", syscalls, syscalls)
        instance = run(image, tenant="t1", permitted=syscalls | {"exit"}, architecture="x86_64")
        assert instance.seal["sealed"] and instance.seal["syscall_count"] == 3
        findings[5] = self.satisfied(
            items[5],
            f"Admission verifies the seal against the linked binary: {instance.seal['syscall_count']} "
            "syscalls, manifest and binary agreeing exactly.",
            *self._evidence("component.py::verify_seal"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        syscalls = frozenset({"read"})
        proven = []
        cases = [
            ("dynamic loading", UnikernelImage("a", "tc", "x86_64", syscalls, syscalls,
                                               features=frozenset({"dlopen"}))),
            ("multi-process", UnikernelImage("b", "tc", "x86_64", syscalls, syscalls,
                                             features=frozenset({"fork"}))),
            ("not single-address-space", UnikernelImage("c", "tc", "x86_64", syscalls, syscalls,
                                                        single_address_space=False)),
            ("manifest drift", UnikernelImage("d", "tc", "x86_64", syscalls,
                                              frozenset({"read", "socket"}))),
        ]
        for label, img in cases:
            try:
                verify_seal(img, permitted=syscalls | {"socket"}, architecture="x86_64")
            except SealInvalid:
                proven.append(label)
        assert len(proven) == 4, proven
        findings[4] = self.satisfied(
            items[4],
            f"Four ways of breaking the seal are all refused: {', '.join(proven)}. The manifest is checked "
            "against the binary, so a claimed seal is never taken at face value.",
            *self._evidence("component.py::verify_seal"))
        findings[2] = self.satisfied(
            items[2],
            "A sealed image has no shell, no exec and no dynamic loading, so there is no ambient path to "
            "run code that was not linked in at build time.",
            *self._evidence("component.py::DISQUALIFYING"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        syscalls = frozenset({"read"})
        arm = UnikernelImage("svc", "tc", "aarch64", syscalls, syscalls)
        try:
            verify_seal(arm, permitted=syscalls, architecture="x86_64")
        except SealInvalid:
            findings[0] = self.satisfied(
                items[0],
                "An image built for a different architecture is refused at admission rather than failing "
                "opaquely at boot.",
                *self._evidence("component.py::verify_seal"))
        return findings

COMPONENT = UnikernelExecutionComponent
