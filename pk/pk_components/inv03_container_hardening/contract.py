"""Binding contract for INV-03 - Container hardening.

Container hardening is the list of things a container should not be allowed to do, checked before it runs: run as root, write to its own filesystem, keep Linux capabilities it never uses, run privileged, or skip a syscall filter. Each finding names the control that failed, and a workload only gets an exception if the exception is written down with an expiry date.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-03"
ELEMENT_NAME = "Container hardening"


def build() -> Contract:
    """Return the production contract for INV-03."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the container hardening baseline: control definitions, pre-admission evaluation, named findings, and time-limited recorded exceptions."
        ),
        owns=[
            "The hardening control baseline",
            "Pre-admission evaluation",
            "Per-control findings",
            "Recorded, expiring exceptions",
            "Baseline versioning"
        ],
        not_owns=[
            "Image content scanning",
            "Runtime intrusion detection",
            "Kernel configuration",
            "Image building",
            "Authorization policy"
        ],
        dependencies=[
            Dependency("INV-02 Container substrate", "upstream", "Supplies the images and specs being hardened"),
            Dependency("GAP-13 Policy engine", "upstream", "Distributes the baseline version in force"),
            Dependency("INV-04 Current orchestration", "downstream", "Admits only workloads that pass"),
            Dependency("INV-44 Wasm hardening system", "peer", "The equivalent baseline for Wasm workloads")
        ],
        source_of_truth="The baseline version in force at admission; an exception is valid only until its recorded expiry.",
        assumptions=[
            "Every peer, network path and store can fail independently",
            "Callers are untrusted until their identity is established",
            "Behaviour must be identical whether a dependency is local or remote"
        ],
        boundaries={
            "tenant": "state and traffic are partitioned per tenant and never shared",
            "environment": "limits and endpoints differ per environment",
            "site": "each site runs its own instance; nothing assumes a global singleton",
            "workload": "budgets and quotas are per workload"
        },
        mandatory=[
            "Refuse root, privileged and writable-root workloads",
            "Require dropped capabilities",
            "Require a syscall filter",
            "Name every failed control",
            "Honour only recorded, unexpired exceptions"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Scanning image contents",
            "Detecting intrusions",
            "Tuning kernels"
        ],
        interfaces={
            "evaluate": "PK_HARDEN_EVAL/1 - spec to per-control findings",
            "exception": "PK_HARDEN_EXCEPTION/1 - control, workload, reason, expiry",
            "baseline": "PK_HARDEN_BASELINE/1 - versioned control set"
        },
        threats=[
            "Container escape via privileged mode",
            "Persistence through writable root filesystem",
            "Permanent exceptions accumulating"
        ],
        failure_modes=[
            "Control failed",
            "Exception expired",
            "Baseline unavailable",
            "Spec incomplete"
        ],
        slos=[
            Slo("baseline enforcement", "zero workloads admitted with an unexcepted failure", "no budget"),
            Slo("exception hygiene", "zero exceptions honoured past expiry", "no budget"),
            Slo("evaluation time", "p99 under 5ms per spec", "1% may exceed")
        ],
        signals={
            "evaluations": "counter",
            "failures": "counter by control",
            "exceptions_active": "gauge"
        },
    )
