"""Binding contract for INV-10 - Component composition system.

The component composition system is what makes modules into something you can actually wire together: each component states its imports and exports as typed interfaces, and composition is linking them. A composition either closes -- every import satisfied by some export -- or it is not a composition at all.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-10"
ELEMENT_NAME = "Component composition system"


def build() -> Contract:
    """Return the production contract for INV-10."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own component linking: satisfy every import from a declared export or refuse the composition, detect dependency cycles, and produce a closed, content-addressed composition whose external imports are exactly what remains unsatisfied."
        ),
        owns=[
            "Component import/export declaration",
            "Link resolution across a composition",
            "Cycle detection",
            "Closure computation and the remaining external imports",
            "Content-addressed composition identity"
        ],
        not_owns=[
            "Module validation",
            "Interface type checking",
            "Runtime instantiation",
            "Host function implementations",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-09 Portable compute ISA", "upstream", "Supplies validated modules to compose"),
            Dependency("INV-11 Interface contract language", "upstream", "Types the interfaces being linked"),
            Dependency("PLN-02 Application plane", "downstream", "Resolves applications built from compositions"),
            Dependency("INV-12 Language interoperability", "peer", "Components may come from different languages")
        ],
        source_of_truth="The composition graph: an import is satisfied only by an export declared in the same composition or listed as external.",
        assumptions=[
            "A component's imports are known before linking",
            "Compositions nest: a composition is itself a component",
            "An unsatisfied import is a deployment error, not a run-time surprise"
        ],
        boundaries={
            "tenant": "compositions do not link across tenants",
            "environment": "external imports are satisfied per environment",
            "site": "a composition is site-independent",
            "workload": "one root composition per workload"
        },
        mandatory=[
            "Satisfy every internal import from a declared export",
            "Refuse a composition with an unsatisfiable import",
            "Detect and refuse dependency cycles",
            "Report the remaining external imports as the composition's own",
            "Produce a deterministic content-addressed identity"
        ],
        optional=[
            "Partial composition for incremental builds",
            "Import aliasing",
            "Dead-export elimination"
        ],
        non_goals=[
            "Validating modules",
            "Checking interface type compatibility in depth",
            "Instantiating at run time",
            "Leaving an import to be resolved by luck at run time"
        ],
        interfaces={
            "component": "PK_COMPONENT/1 - a component with typed imports and exports",
            "compose": "PK_COMPOSITION/1 - a closed composition and its external imports"
        },
        threats=[
            "An import silently satisfied by an unintended export",
            "Cycle causing infinite instantiation",
            "Composition identity collision between different graphs",
            "Import injection through a crafted export name"
        ],
        failure_modes=[
            "Import has no matching export",
            "Dependency cycle",
            "Two components export the same interface ambiguously",
            "External import not available in the environment"
        ],
        slos=[
            Slo("closure", "zero compositions published with an unsatisfied internal import", "no budget"),
            Slo("determinism", "identical component sets produce an identical composition id", "no budget"),
            Slo("link latency", "p99 under 200ms for 200-component compositions", "1% may exceed")
        ],
        signals={
            "compositions": "counter by outcome",
            "unsatisfied_imports": "counter by interface name",
            "cycles_detected": "counter",
            "external_imports": "gauge per published composition"
        },
    )
