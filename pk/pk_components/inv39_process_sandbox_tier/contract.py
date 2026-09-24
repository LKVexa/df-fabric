"""Binding contract for INV-39 - Process sandbox tier.

The process sandbox tier is seccomp, namespaces and a dropped capability set: cheap, fast, and sharing a kernel with everything else on the box. It is the right tier for trusted code and the wrong one for anything hostile, so this element states the residual kernel attack surface instead of quietly calling itself isolation.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-39"
ELEMENT_NAME = "Process sandbox tier"


def build() -> Contract:
    """Return the production contract for INV-39."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the process-level sandbox: apply a default-deny syscall filter, drop all ambient capabilities, enter every namespace the profile requires, and report the residual kernel attack surface rather than presenting this tier as equivalent to a VM."
        ),
        owns=[
            "The seccomp syscall allow-list per profile",
            "Capability dropping",
            "Namespace entry and its completeness",
            "Residual kernel attack-surface reporting",
            "Refusal to start with an incomplete profile"
        ],
        not_owns=[
            "The kernel",
            "Hardware isolation",
            "Other tiers",
            "Container image formats",
            "Placement"
        ],
        dependencies=[
            Dependency("PLN-04 Execution plane", "upstream", "Admits only trusted-class workloads to this tier"),
            Dependency("GAP-13 Policy engine", "upstream", "Supplies the sandbox profile policy"),
            Dependency("INV-45 SFI mechanisms", "peer", "Adds in-process isolation on top of the sandbox", required=False),
            Dependency("GAP-09 Unified observability", "downstream", "Receives syscall-denial signals")
        ],
        source_of_truth="The applied seccomp filter and capability set as read back from the running process, not the profile that was requested.",
        assumptions=[
            "This tier shares a kernel with every other process on the node",
            "A kernel bug defeats this tier entirely",
            "A profile that fails to apply leaves the process unconfined"
        ],
        boundaries={
            "tenant": "a sandboxed process serves one tenant and shares a kernel with others",
            "environment": "profiles differ per environment",
            "site": "kernel version differences change which filters apply",
            "workload": "one profile per workload"
        },
        mandatory=[
            "Deny syscalls by default and allow only the profile's list",
            "Drop every ambient capability not explicitly retained",
            "Enter all namespaces the profile requires or refuse to start",
            "Verify the applied filter by reading it back",
            "Report the residual kernel surface as syscall count"
        ],
        optional=[
            "Landlock filesystem restriction",
            "User-namespace remapping",
            "Per-syscall argument filtering"
        ],
        non_goals=[
            "Claiming VM-equivalent isolation",
            "Protecting against kernel bugs",
            "Running untrusted or hostile code",
            "Namespace-only confinement without seccomp"
        ],
        interfaces={
            "profile": "PK_SANDBOX_PROFILE/1 - syscalls, capabilities and namespaces",
            "apply": "PK_SANDBOX_APPLIED/1 - the verified applied state and residual surface"
        },
        threats=[
            "A kernel bug reached through an allowed syscall",
            "A profile that silently fails to apply",
            "Capability retention granting ambient authority",
            "Namespace omission leaving a shared view of the host"
        ],
        failure_modes=[
            "Profile fails to apply",
            "Required namespace unavailable on this kernel",
            "Retained capability outside the permitted set",
            "Syscall allow-list larger than the budget"
        ],
        slos=[
            Slo("default deny", "zero processes started without an applied default-deny filter", "no budget"),
            Slo("capability drop", "zero processes retaining an unpermitted capability", "no budget"),
            Slo("surface budget", "allow-lists at or below the declared syscall budget", "breaches are reported, not blocked")
        ],
        signals={
            "sandbox_starts": "counter by profile and outcome",
            "syscall_denials": "counter by syscall",
            "residual_syscalls": "gauge of allow-list size per profile",
            "profile_failures": "counter by reason",
            "retained_capabilities": "gauge per profile"
        },
    )
