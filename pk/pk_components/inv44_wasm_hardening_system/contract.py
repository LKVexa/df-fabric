"""Binding contract for INV-44 - Wasm hardening system.

The Wasm hardening system is what turns a Wasm runtime from a portability layer into an isolation boundary: guard pages, control-flow integrity, bounded fuel, and a compiler whose output is verified rather than trusted. A hardened runtime with one of these off is not a hardened runtime, and this element says so.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-44"
ELEMENT_NAME = "Wasm hardening system"


def build() -> Contract:
    """Return the production contract for INV-44."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the hardened Wasm runtime configuration: require the full hardening set, verify compiled module output before execution, enforce fuel and memory ceilings at run time, and refuse to execute under a partial hardening configuration."
        ),
        owns=[
            "The required hardening feature set",
            "Post-compilation output verification",
            "Fuel metering and its exhaustion behaviour",
            "Linear-memory ceiling enforcement",
            "Refusal of partially hardened configurations"
        ],
        not_owns=[
            "The Wasm specification",
            "Compiler implementation",
            "Module source",
            "The host image",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-45 SFI mechanisms", "upstream", "Supplies the isolation primitives this hardening composes"),
            Dependency("INV-29 Hybrid Wasm/unikernel", "downstream", "Consumes a hardened runtime as its inner layer"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads to the Wasm tier"),
            Dependency("INV-41 Capability security", "peer", "Imports are capabilities, not ambient functions")
        ],
        source_of_truth="The verified configuration of the running engine; a hardening flag requested but not applied does not count.",
        assumptions=[
            "A compiler bug can produce module code that escapes the sandbox",
            "An unmetered module can spin forever",
            "Linear memory grows on demand and must be capped"
        ],
        boundaries={
            "tenant": "one engine instance serves one tenant",
            "environment": "fuel and memory ceilings differ per environment",
            "site": "guard-page support depends on the host address space",
            "workload": "one module instance per workload"
        },
        mandatory=[
            "Require every hardening feature in the declared set",
            "Verify compiled output before it executes",
            "Meter execution with fuel and trap on exhaustion",
            "Cap linear-memory growth at the declared ceiling",
            "Refuse execution when any hardening feature is inactive"
        ],
        optional=[
            "Interpreter fallback for unverifiable modules",
            "Per-import fuel accounting",
            "Ahead-of-time compilation with a signed cache"
        ],
        non_goals=[
            "Implementing the compiler",
            "Extending the Wasm specification",
            "Running unhardened for performance",
            "Trusting compiler output unverified"
        ],
        interfaces={
            "configure": "PK_WASM_HARDENING/1 - the hardening feature set and its applied state",
            "instantiate": "PK_WASM_INSTANCE/1 - a verified, metered module instance"
        },
        threats=[
            "A compiler bug producing escaping code",
            "Fuel metering disabled for performance",
            "Linear memory growing until the host OOMs",
            "Guard pages absent on a constrained address space"
        ],
        failure_modes=[
            "A hardening feature is inactive",
            "Compiled output fails verification",
            "Fuel exhausted mid-execution",
            "Memory growth request exceeds the ceiling"
        ],
        slos=[
            Slo("hardening completeness", "zero instances executed with a partial hardening set", "no budget"),
            Slo("output verification", "100% of compiled modules verified before execution", "no budget"),
            Slo("memory ceiling", "zero instances growing past their declared ceiling", "no budget")
        ],
        signals={
            "instances": "gauge by tenant and hardening profile",
            "hardening_refusals": "counter by missing feature",
            "verification_failures": "counter of modules whose compiled output failed verification",
            "fuel_exhaustions": "counter of traps on fuel exhaustion",
            "memory_growth_refusals": "counter of refused grow requests"
        },
    )
