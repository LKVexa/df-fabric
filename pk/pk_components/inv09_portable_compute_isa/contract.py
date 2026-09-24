"""Binding contract for INV-09 - Portable compute ISA.

The portable compute ISA is the bytecode everything above it compiles to: a small, deterministic instruction set with no ambient environment and no undefined behaviour to exploit. Portability is only worth anything if the same module computes the same answer everywhere, so this element validates modules rather than trusting their headers.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-09"
ELEMENT_NAME = "Portable compute ISA"


def build() -> Contract:
    """Return the production contract for INV-09."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own module validation and the deterministic execution profile: verify structure, types and the declared feature set before a module runs, and refuse any module using a non-deterministic or unapproved feature."
        ),
        owns=[
            "Module structural and type validation",
            "The approved feature set per profile",
            "Determinism profile enforcement",
            "Refusal of unvalidated or over-featured modules",
            "Module size and section limits"
        ],
        not_owns=[
            "Compilers producing modules",
            "Runtime hardening",
            "The component model above it",
            "Host function semantics",
            "Placement"
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Declares which feature profile an environment permits"),
            Dependency("INV-10 Component composition system", "downstream", "Composes validated modules into components"),
            Dependency("INV-44 Wasm hardening system", "downstream", "Hardens the engine executing these modules"),
            Dependency("GAP-15 Runtime compatibility certification", "peer", "Certifies module/engine version pairs")
        ],
        source_of_truth="The validation result over the module bytes; a declared feature the bytes do not support, or use of one the profile forbids, both fail.",
        assumptions=[
            "A module may declare features it does not use, and use features it does not declare",
            "Floating-point and SIMD introduce determinism hazards across hosts",
            "Validation is cheap relative to the cost of running an invalid module"
        ],
        boundaries={
            "tenant": "modules are tenant-scoped; validation results are not shared across tenants",
            "environment": "feature profiles differ per environment",
            "site": "a site may lack the hardware a feature needs",
            "workload": "one module per workload instance"
        },
        mandatory=[
            "Validate structure and types before execution",
            "Refuse features outside the environment's profile",
            "Detect declared-but-unsupported and used-but-undeclared features",
            "Enforce section and size limits",
            "Guarantee the determinism profile or refuse the module"
        ],
        optional=[
            "SIMD under an explicit opt-in",
            "Relaxed float semantics for non-deterministic profiles",
            "Streaming validation for large modules"
        ],
        non_goals=[
            "Compiling source to bytecode",
            "Hardening the engine",
            "Running an unvalidated module",
            "Guaranteeing determinism for opted-out profiles"
        ],
        interfaces={
            "validate": "PK_MODULE_VALIDATION/1 - validation verdict with the feature set actually used",
            "profile": "PK_ISA_PROFILE/1 - permitted features and determinism class"
        },
        threats=[
            "A module using an undeclared feature to escape validation",
            "Non-deterministic float results diverging between replicas",
            "Section-count explosion as a denial-of-service",
            "Profile downgrade permitting a hazardous feature"
        ],
        failure_modes=[
            "Module fails structural validation",
            "Feature used outside the profile",
            "Declared feature unsupported by the engine",
            "Module exceeds a section limit"
        ],
        slos=[
            Slo("validation soundness", "zero modules executed without passing validation", "no budget"),
            Slo("determinism", "identical modules and inputs produce identical results within a deterministic profile", "no budget"),
            Slo("validation latency", "p99 under 20ms for modules up to 4MiB", "1% may exceed")
        ],
        signals={
            "modules_validated": "counter by profile and outcome",
            "feature_refusals": "counter by feature",
            "validation_seconds": "histogram by module size",
            "determinism_profile": "gauge of modules per profile"
        },
    )
