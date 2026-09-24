"""Binding contract for INV-29 - Hybrid Wasm/unikernel.

The hybrid Wasm/unikernel model puts a Wasm runtime inside a unikernel image: the module gets the component model's portability and the unikernel's hardware-backed boundary at once. The point is defence in depth, so this element refuses a composition where one layer's guarantees silently substitute for the other's.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-29"
ELEMENT_NAME = "Hybrid Wasm/unikernel"


def build() -> Contract:
    """Return the production contract for INV-29."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the composition of a Wasm runtime inside a unikernel image: verify that both layers are independently sound, that the Wasm module's imports are a subset of what the unikernel actually exposes, and refuse a composition relying on only one layer."
        ),
        owns=[
            "Composition of a Wasm module with a unikernel host image",
            "Import/export reconciliation across the two layers",
            "Independent verification of each layer",
            "Defence-in-depth invariant enforcement",
            "Refusal when a layer is degraded to a pass-through"
        ],
        not_owns=[
            "The Wasm runtime implementation",
            "Unikernel toolchains",
            "Module compilation",
            "The hypervisor",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-27 Unikernel execution", "upstream", "Supplies the verified sealed host image"),
            Dependency("INV-44 Wasm hardening system", "upstream", "Supplies the hardened Wasm runtime configuration"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits workloads to this hybrid tier"),
            Dependency("INV-30 Capability hardware sandbox", "peer", "May add a third hardware-enforced layer", required=False)
        ],
        source_of_truth="The composition record: both layers must independently verify, and the record names which guarantee comes from which layer.",
        assumptions=[
            "A Wasm module's imports must be satisfied by the host image, not by the hypervisor",
            "Either layer alone is weaker than both together",
            "A misconfigured composition can silently reduce to one layer"
        ],
        boundaries={
            "tenant": "a composition serves exactly one tenant",
            "environment": "required layer count differs per environment",
            "site": "a site must support both layers to run the hybrid tier",
            "workload": "one Wasm module per composition"
        },
        mandatory=[
            "Verify the unikernel host image independently",
            "Verify the Wasm module's hardening independently",
            "Require every module import to be exposed by the host image",
            "Refuse a composition where either layer is absent or disabled",
            "Record which guarantee each layer contributes"
        ],
        optional=[
            "Ahead-of-time module compilation into the image",
            "Multi-module compositions",
            "Third hardware-enforced layer"
        ],
        non_goals=[
            "Implementing the Wasm runtime",
            "Building unikernel images",
            "Treating one strong layer as equivalent to two",
            "Satisfying module imports from the host kernel"
        ],
        interfaces={
            "compose": "PK_HYBRID_COMPOSITION/1 - compose a module with a host image",
            "verify": "PK_HYBRID_VERIFICATION/1 - per-layer verification results"
        },
        threats=[
            "A composition reduced to Wasm-only when the unikernel layer is misconfigured",
            "Module imports satisfied by an escape hatch outside the host image",
            "Layer confusion: relying on the sandbox for isolation the hypervisor was meant to give",
            "Import surface growth going unreviewed"
        ],
        failure_modes=[
            "A module import is not exposed by the host image",
            "One layer fails verification",
            "Layer count below the environment's requirement",
            "Host image and module target different architectures"
        ],
        slos=[
            Slo("layer count", "zero compositions admitted with fewer layers than the environment requires", "no budget"),
            Slo("import closure", "zero modules admitted with an unsatisfied import", "no budget"),
            Slo("verification independence", "both layers verified separately for every composition", "no budget")
        ],
        signals={
            "compositions": "counter by outcome and layer count",
            "import_refusals": "counter of unsatisfied module imports",
            "layer_failures": "counter by layer and reason",
            "hybrid_instances": "gauge by tenant"
        },
    )
