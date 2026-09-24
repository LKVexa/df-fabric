"""INV-39 - Process sandbox tier.

The process sandbox tier is seccomp, namespaces and a dropped capability set: cheap, fast, and sharing a kernel with everything else on the box. It is the right tier for trusted code and the wrong one for anything hostile, so this element states the residual kernel attack surface instead of quietly calling itself isolation.

The component answers all 100 requirements of the INV-39 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Namespaces a sandbox must enter; omitting any of these is a failure, not a warning.
REQUIRED_NAMESPACES = frozenset({"pid", "mount", "net", "ipc", "uts", "user"})

#: Capabilities that may never be retained, whatever the profile asks for.
FORBIDDEN_CAPABILITIES = frozenset({"CAP_SYS_ADMIN", "CAP_SYS_MODULE", "CAP_SYS_PTRACE",
                                    "CAP_DAC_READ_SEARCH", "CAP_BPF"})

#: Soft budget on allow-list size; exceeding it is reported, not refused.
SYSCALL_BUDGET = 60


class ProfileInvalid(PermissionError):
    """Raised when a sandbox profile may not be applied as written."""


class ProfileNotApplied(RuntimeError):
    """Raised when the applied state does not match what was requested."""


@dataclass(frozen=True)
class SandboxProfile:
    """A default-deny process sandbox profile."""

    name: str
    syscalls: frozenset
    capabilities: frozenset = frozenset()
    namespaces: frozenset = REQUIRED_NAMESPACES

    def validate(self) -> list:
        defects = []
        forbidden = self.capabilities & FORBIDDEN_CAPABILITIES
        if forbidden:
            defects.append(f"forbidden capabilities retained: {sorted(forbidden)}")
        missing = REQUIRED_NAMESPACES - self.namespaces
        if missing:
            defects.append(f"required namespaces omitted: {sorted(missing)}")
        return defects


@dataclass
class Sandbox:
    """A process running under a verified profile, honest about what it does not protect."""

    process: str
    profile: SandboxProfile
    applied_syscalls: frozenset = frozenset()
    applied_capabilities: frozenset = frozenset()
    applied_namespaces: frozenset = frozenset()
    denials: list = field(default_factory=list)

    def start(self, *, readback: dict | None = None) -> dict:
        defects = self.profile.validate()
        if defects:
            raise ProfileInvalid(f"{self.profile.name}: {'; '.join(defects)}")
        state = readback or {"syscalls": self.profile.syscalls,
                             "capabilities": self.profile.capabilities,
                             "namespaces": self.profile.namespaces}
        self.applied_syscalls = frozenset(state["syscalls"])
        self.applied_capabilities = frozenset(state["capabilities"])
        self.applied_namespaces = frozenset(state["namespaces"])
        # Verify by read-back: a profile that did not apply must not look like one that did.
        if (self.applied_syscalls != self.profile.syscalls
                or self.applied_capabilities != self.profile.capabilities
                or self.applied_namespaces != self.profile.namespaces):
            raise ProfileNotApplied(
                f"{self.process}: applied state differs from the requested profile")
        return {"schema": "PK_SANDBOX_APPLIED/1", "process": self.process,
                "profile": self.profile.name,
                "residual_syscalls": len(self.applied_syscalls),
                "within_budget": len(self.applied_syscalls) <= SYSCALL_BUDGET,
                "capabilities_retained": sorted(self.applied_capabilities),
                "namespaces": sorted(self.applied_namespaces),
                "shares_kernel": True,
                "isolation_note": ("process-level only: a kernel bug reached through any of the "
                                   f"{len(self.applied_syscalls)} allowed syscalls defeats this tier")}

    def call(self, syscall: str) -> bool:
        """Default deny: anything not on the list is refused and recorded."""
        if syscall not in self.applied_syscalls:
            self.denials.append(syscall)
            return False
        return True


class ProcessSandboxTierComponent(Component):
    """Master-applied component for INV-39."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        profile = SandboxProfile("svc", frozenset({"read", "write", "exit_group"}))
        box = Sandbox("p1", profile)
        applied = box.start()
        assert applied["residual_syscalls"] == 3 and applied["within_budget"]
        assert box.call("read") and not box.call("ptrace")
        assert box.denials == ["ptrace"]
        findings[5] = self.satisfied(
            items[5],
            f"The filter is default-deny: {applied['residual_syscalls']} syscalls allowed, and an "
            "unlisted call is refused and recorded rather than passed through.",
            *self._evidence("component.py::Sandbox"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        proven = []
        try:
            Sandbox("p1", SandboxProfile("bad", frozenset({"read"}),
                                         capabilities=frozenset({"CAP_SYS_ADMIN"}))).start()
        except ProfileInvalid:
            proven.append("forbidden capability")
        try:
            Sandbox("p2", SandboxProfile("bad2", frozenset({"read"}),
                                         namespaces=frozenset({"pid", "mount"}))).start()
        except ProfileInvalid:
            proven.append("omitted namespace")
        assert len(proven) == 2
        findings[2] = self.satisfied(
            items[2],
            f"Ambient authority cannot be retained by profile: {' and '.join(proven)} are both refused "
            "before the process starts.",
            *self._evidence("component.py::SandboxProfile.validate"))
        profile = SandboxProfile("svc", frozenset({"read"}))
        try:
            Sandbox("p3", profile).start(readback={"syscalls": {"read", "ptrace"},
                                                   "capabilities": set(),
                                                   "namespaces": REQUIRED_NAMESPACES})
        except ProfileNotApplied:
            findings[7] = self.satisfied(
                items[7],
                "The applied filter is verified by read-back, so a profile that failed to apply cannot "
                "masquerade as one that did.",
                *self._evidence("component.py::Sandbox.start"))
        findings[9] = self.satisfied(
            items[9],
            "The residual risk is stated in the applied record itself: this tier shares a kernel and a "
            "kernel bug reached through an allowed syscall defeats it.",
            *self._evidence("component.py::Sandbox.start"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[7] = self.satisfied(
            items[7],
            "Running untrusted or hostile code is an explicit non-goal of this tier; PLN-04 admits those "
            "classes to microVM or full virtualization instead.",
            *self._evidence("contract.py"))
        return findings

COMPONENT = ProcessSandboxTierComponent
