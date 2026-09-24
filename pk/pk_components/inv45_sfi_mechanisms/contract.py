"""Binding contract for INV-45 - SFI mechanisms.

Software fault isolation is the fallback when hardware will not help: masking every memory access into a sandbox region so a compromised module cannot reach outside it. It is cheap and portable, and it is only as good as the guarantee that every access really was rewritten -- so this element verifies that rather than assuming it.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-45"
ELEMENT_NAME = "SFI mechanisms"


def build() -> Contract:
    """Return the production contract for INV-45."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own software fault isolation: confine memory accesses to a sandbox region by masking, verify that every access in a module was actually rewritten, and refuse to load a module containing an unmasked access."
        ),
        owns=[
            "The sandbox region and its mask",
            "Access rewriting verification",
            "Indirect-branch target confinement",
            "Refusal of modules with unmasked accesses",
            "The measured overhead of masking"
        ],
        not_owns=[
            "Hardware capability enforcement",
            "Compilers",
            "The Wasm specification",
            "Other isolation tiers",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-30 Capability hardware sandbox", "upstream", "Preferred where the hardware exists; this element is the fallback"),
            Dependency("INV-44 Wasm hardening system", "downstream", "Composes these primitives into the hardened runtime"),
            Dependency("INV-39 Process sandbox tier", "peer", "Adds in-process isolation beneath the syscall filter", required=False),
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Determines whether the hardware alternative exists")
        ],
        source_of_truth="The verification pass over the loaded module; a module is confined only if every access was proven rewritten.",
        assumptions=[
            "A single unmasked access defeats the whole scheme",
            "Indirect branches can reach unintended targets without confinement",
            "Masking costs measurable performance on every access"
        ],
        boundaries={
            "tenant": "a sandbox region belongs to one module of one tenant",
            "environment": "region sizes differ per environment",
            "site": "portable by design; no site-specific hardware required",
            "workload": "one region per module instance"
        },
        mandatory=[
            "Confine every memory access to the sandbox region by masking",
            "Verify that every access in the module was rewritten",
            "Confine indirect-branch targets to a permitted target set",
            "Refuse to load a module with an unmasked access",
            "Report the measured masking overhead"
        ],
        optional=[
            "Region-size specialisation to avoid masking",
            "Hardware acceleration where available",
            "Partial verification with an interpreter fallback"
        ],
        non_goals=[
            "Replacing hardware capability enforcement where it exists",
            "Implementing a compiler",
            "Confining accesses that were never rewritten",
            "Claiming isolation from an unverified module"
        ],
        interfaces={
            "load": "PK_SFI_MODULE/1 - load a module after verifying every access is masked",
            "mask": "PK_SFI_MASK/1 - the region base, size and mask applied to accesses"
        },
        threats=[
            "An unmasked access reaching outside the region",
            "An indirect branch landing on an unintended target",
            "Verification skipped for performance",
            "Region size chosen so the mask does not actually confine"
        ],
        failure_modes=[
            "Module contains an unmasked access",
            "Indirect target outside the permitted set",
            "Region size is not a power of two",
            "Verification pass incomplete"
        ],
        slos=[
            Slo("confinement", "zero accesses served outside the sandbox region", "no budget"),
            Slo("verification", "100% of loaded modules fully verified", "no budget"),
            Slo("overhead", "masking overhead at or below 15%", "measured and reported per module")
        ],
        signals={
            "modules_loaded": "counter by outcome",
            "unmasked_accesses": "counter of accesses that failed verification",
            "branch_confinements": "counter of indirect branches clamped to the target set",
            "masking_overhead_percent": "gauge per module"
        },
    )
