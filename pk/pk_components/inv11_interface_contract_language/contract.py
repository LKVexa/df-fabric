"""Binding contract for INV-11 - Interface contract language.

The interface contract language is WIT: the typed vocabulary that says what crosses a component boundary. It is the only thing standing between two components written in different languages and a memory-safety incident, so compatibility here is structural and checked, never assumed from a version number.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-11"
ELEMENT_NAME = "Interface contract language"


def build() -> Contract:
    """Return the production contract for INV-11."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own interface type definitions and compatibility: decide whether two versions of an interface can be linked by comparing their structure, and classify every change as compatible, breaking, or additive."
        ),
        owns=[
            "Interface type definitions and their structure",
            "Structural compatibility checking",
            "Change classification (additive, compatible, breaking)",
            "Version semantics for interfaces",
            "Refusal to link structurally incompatible interfaces"
        ],
        not_owns=[
            "Bindings generation",
            "Component linking",
            "Runtime marshalling",
            "Language-specific type mapping",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-09 Portable compute ISA", "upstream", "Supplies the value types interfaces are built from"),
            Dependency("INV-10 Component composition system", "downstream", "Links only interfaces this element says are compatible"),
            Dependency("INV-12 Language interoperability", "downstream", "Generates bindings from these definitions"),
            Dependency("GAP-15 Runtime compatibility certification", "peer", "Certifies interface/runtime pairs")
        ],
        source_of_truth="The interface's structure; a version number is a label, and compatibility is decided by comparing types.",
        assumptions=[
            "Producers and consumers evolve independently",
            "Adding a result case breaks consumers; adding a function does not",
            "A version bump may or may not be breaking, and the number does not say which"
        ],
        boundaries={
            "tenant": "interface definitions are estate-wide vocabulary",
            "environment": "an environment may pin interface versions",
            "site": "interfaces are site-independent",
            "workload": "a workload depends on interface versions, not component versions"
        },
        mandatory=[
            "Define every interface structurally, not by name alone",
            "Decide compatibility by comparing structure",
            "Classify each change as additive, compatible, or breaking",
            "Refuse to link structurally incompatible interfaces",
            "Treat a removed or narrowed type as breaking"
        ],
        optional=[
            "Semantic version inference from the change class",
            "Interface deprecation timers",
            "Automatic adapter generation for compatible changes"
        ],
        non_goals=[
            "Generating language bindings",
            "Linking components",
            "Marshalling values at run time",
            "Inferring compatibility from a version string"
        ],
        interfaces={
            "define": "PK_INTERFACE/1 - a typed interface definition",
            "compare": "PK_INTERFACE_DIFF/1 - change class between two interface versions"
        },
        threats=[
            "Type confusion between producer and consumer",
            "A breaking change shipped as a patch version",
            "Structural equality assumed from matching names",
            "Consumer reading a result case it does not handle"
        ],
        failure_modes=[
            "Structurally incompatible interfaces",
            "Function removed from an interface",
            "Parameter type narrowed",
            "New result case a consumer cannot handle"
        ],
        slos=[
            Slo("compatibility soundness", "zero links permitted between structurally incompatible interfaces", "no budget"),
            Slo("classification accuracy", "every change classified before publication", "no budget"),
            Slo("comparison latency", "p99 under 5ms per interface pair", "1% may exceed")
        ],
        signals={
            "interfaces_defined": "gauge by package",
            "change_classes": "counter by additive, compatible, breaking",
            "link_refusals": "counter by incompatibility reason",
            "breaking_changes": "counter by interface"
        },
    )
