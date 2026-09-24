"""Binding contract for INV-12 - Language interoperability.

Language interoperability is the promise that a Rust component and a Go component can call each other without either one learning the other's memory layout. It works by never sharing memory at all: values are lowered into the canonical ABI on the way out and lifted on the way in, and a type a language cannot represent is a build error rather than a silent truncation.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-12"
ELEMENT_NAME = "Language interoperability"


def build() -> Contract:
    """Return the production contract for INV-12."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own canonical lifting and lowering across the language boundary: map every interface type to each guest language's representation, refuse a mapping that would lose information, and guarantee no memory is shared between components."
        ),
        owns=[
            "Canonical ABI lifting and lowering",
            "Per-language type mapping tables",
            "Refusal of lossy mappings",
            "Ownership transfer semantics at the boundary",
            "The no-shared-memory guarantee between components"
        ],
        not_owns=[
            "Compilers and toolchains",
            "Interface definitions",
            "Composition linking",
            "Host function implementations",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-11 Interface contract language", "upstream", "Supplies the interface types being mapped"),
            Dependency("INV-10 Component composition system", "upstream", "Determines which components call each other"),
            Dependency("INV-13 System interface", "downstream", "Uses the same canonical ABI for host calls"),
            Dependency("INV-45 SFI mechanisms", "peer", "Confines each component's linear memory independently")
        ],
        source_of_truth="The canonical ABI representation; a guest language's native type is a projection of it, never the other way round.",
        assumptions=[
            "Guest languages have different integer widths, string encodings and ownership models",
            "A type one language cannot represent exactly must fail loudly",
            "Sharing linear memory between components would defeat the isolation entirely"
        ],
        boundaries={
            "tenant": "no memory crosses a component boundary, let alone a tenant one",
            "environment": "supported language set differs per environment",
            "site": "language support is site-independent",
            "workload": "each component has its own linear memory"
        },
        mandatory=[
            "Lower every outgoing value into the canonical ABI",
            "Lift every incoming value from the canonical ABI",
            "Refuse a type mapping that would lose precision or information",
            "Transfer ownership explicitly; never alias across the boundary",
            "Guarantee components share no linear memory"
        ],
        optional=[
            "Zero-copy for same-language pairs under proof",
            "Lazy lifting for large lists",
            "Additional guest-language backends"
        ],
        non_goals=[
            "Writing compilers",
            "Defining interfaces",
            "Sharing memory for performance",
            "Silently truncating a value to make a mapping work"
        ],
        interfaces={
            "lower": "PK_CANONICAL_LOWER/1 - a guest value lowered into the canonical ABI",
            "lift": "PK_CANONICAL_LIFT/1 - a canonical value lifted into a guest representation",
            "mapping": "PK_TYPE_MAPPING/1 - per-language representation of an interface type"
        },
        threats=[
            "Silent truncation converting u64 to a 53-bit float",
            "Aliased memory letting one component read another's heap",
            "String encoding confusion producing invalid data",
            "Ownership double-free across the boundary"
        ],
        failure_modes=[
            "Type unrepresentable in the target language",
            "Value out of range for the target representation",
            "Encoding conversion fails",
            "Ownership transferred twice"
        ],
        slos=[
            Slo("no loss", "zero values silently truncated or re-encoded lossily", "no budget"),
            Slo("no sharing", "zero bytes of linear memory shared between components", "no budget"),
            Slo("boundary cost", "p99 lowering+lifting under 2us for scalar values", "1% may exceed")
        ],
        signals={
            "boundary_calls": "counter by language pair and interface",
            "mapping_refusals": "counter by type and language",
            "range_violations": "counter of values outside the target representation",
            "ownership_transfers": "counter by direction"
        },
    )
