"""Binding contract for INV-27 - Unikernel execution.

Unikernel execution is the single-address-space bet: the application and its kernel are linked into one image with no shell, no second process and no syscall surface to abuse. The isolation argument only holds if the image really is sealed, so this element verifies the seal rather than assuming it.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-27"
ELEMENT_NAME = "Unikernel execution"


def build() -> Contract:
    """Return the production contract for INV-27."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own unikernel image admission and execution: verify that an image is genuinely single-address-space and sealed -- no multi-process support, no dynamic loading, a closed syscall set -- and refuse to run one that is not."
        ),
        owns=[
            "Unikernel image seal verification",
            "The permitted syscall set per image",
            "Single-address-space enforcement",
            "Refusal of dynamically-linked or multi-process images",
            "Image entry-point and boot contract"
        ],
        not_owns=[
            "Building unikernel images",
            "The hypervisor beneath",
            "Language runtimes",
            "Device models",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-28 Unikernel implementations", "upstream", "Supplies the concrete unikernel toolchains and their image formats"),
            Dependency("INV-23 Hardware virtualization primitive", "upstream", "Provides the isolation boundary the image runs inside"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads to the unikernel tier"),
            Dependency("INV-29 Hybrid Wasm/unikernel", "peer", "Shares the sealed-image model for Wasm payloads")
        ],
        source_of_truth="The image's own seal manifest, verified against the loaded binary; a claim in metadata is not a seal.",
        assumptions=[
            "A unikernel image cannot fork, exec, or load code at run time",
            "The syscall set is fixed at link time",
            "An image built by an untrusted toolchain may claim a seal it does not have"
        ],
        boundaries={
            "tenant": "one image serves one tenant; images are not shared",
            "environment": "permitted syscall sets differ per environment",
            "site": "a site runs only images whose architecture it supports",
            "workload": "one workload is one image"
        },
        mandatory=[
            "Verify the image is single-address-space before execution",
            "Verify the declared syscall set matches the linked binary",
            "Refuse images supporting fork, exec, or dynamic loading",
            "Refuse an image whose seal cannot be verified",
            "Record the verified seal with the running instance"
        ],
        optional=[
            "Syscall-set minimisation reports",
            "Image size budgets",
            "Build-toolchain attestation"
        ],
        non_goals=[
            "Building images",
            "Providing a shell or debugger inside the guest",
            "Supporting multi-process workloads",
            "Trusting a metadata claim of sealing"
        ],
        interfaces={
            "admit": "PK_UNIKERNEL_IMAGE/1 - submit an image with its seal manifest",
            "run": "PK_UNIKERNEL_INSTANCE/1 - a running instance and its verified seal"
        },
        threats=[
            "An image claiming a seal it does not have",
            "Dynamic loading reintroducing arbitrary code",
            "Syscall-set drift between manifest and binary",
            "Debug builds shipping a shell into production"
        ],
        failure_modes=[
            "Seal verification fails",
            "Syscall set differs from the manifest",
            "Image supports fork or exec",
            "Architecture unsupported at this site"
        ],
        slos=[
            Slo("seal soundness", "zero images executed without a verified seal", "no budget"),
            Slo("syscall fidelity", "zero images running with syscalls outside their verified set", "no budget"),
            Slo("admission latency", "p99 verification under 100ms", "1% may exceed")
        ],
        signals={
            "images_admitted": "counter by toolchain and outcome",
            "seal_failures": "counter by reason",
            "syscall_set_size": "histogram of verified syscall-set sizes",
            "unikernel_instances": "gauge by tenant"
        },
    )
