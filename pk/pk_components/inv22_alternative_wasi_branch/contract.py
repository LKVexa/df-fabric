"""Binding contract for INV-22 - Alternative WASI branch.

The alternative WASI branch exists because the standards track is not the only consumer of these interfaces, and a fork that ships earlier will accumulate divergence. This element's job is to know exactly where the branches differ, translate what can be translated, and refuse -- loudly -- what cannot, rather than letting a component silently behave differently on each.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-22"
ELEMENT_NAME = "Alternative WASI branch"


def build() -> Contract:
    """Return the production contract for INV-22."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own branch divergence management: an explicit compatibility matrix per interface, bidirectional translation where semantics permit, refusal where they do not, and a conformance report that states which branch a component was certified against."
        ),
        owns=[
            "The per-interface compatibility matrix",
            "Bidirectional shims where semantics match",
            "Explicit refusal for semantically divergent interfaces",
            "Branch certification of a component",
            "Divergence drift reporting"
        ],
        not_owns=[
            "Either branch's specification",
            "Guest toolchains",
            "Runtime implementation",
            "Standards process",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-13 System interface", "upstream", "The standards-track interfaces being compared"),
            Dependency("INV-11 Interface contract language", "upstream", "Both branches are expressed in it"),
            Dependency("INV-12 Language interoperability", "peer", "Shims reuse the canonical ABI mappings"),
            Dependency("INV-10 Component composition system", "downstream", "Refuses to link components certified against incompatible branches"),
            Dependency("GAP-14 Conformance certification", "downstream", "Records which branch a component passed against")
        ],
        source_of_truth="The compatibility matrix; a component's certified branch is recorded, and an interface absent from the matrix is treated as divergent until it is classified.",
        assumptions=[
            "Divergence grows over time unless it is measured",
            "Some divergence is cosmetic and shimmable; some is semantic and is not",
            "Silently running on the wrong branch is worse than refusing to run"
        ],
        boundaries={
            "tenant": "branch selection is a platform property, not a tenant one",
            "environment": "different environments may standardise on different branches",
            "site": "a site runs one branch at a time",
            "workload": "each workload is certified against exactly one branch"
        },
        mandatory=[
            "Maintain an explicit per-interface compatibility classification",
            "Treat an unclassified interface as divergent, never as compatible",
            "Shim only where semantics genuinely match",
            "Refuse to run a component on a branch it is not certified for",
            "Report divergence drift over time"
        ],
        optional=[
            "Automatic matrix generation from interface definitions",
            "Dual certification for interfaces that are identical",
            "Deprecation timelines per divergent interface"
        ],
        non_goals=[
            "Influencing either standards process",
            "Implementing a runtime",
            "Papering over semantic divergence with a lossy shim",
            "Guessing at an unclassified interface"
        ],
        interfaces={
            "matrix": "PK_BRANCH_MATRIX/1 - per-interface compatibility classification",
            "translate": "PK_BRANCH_SHIM/1 - a bidirectional shim for a compatible interface",
            "certify": "PK_BRANCH_CERT/1 - the branch a component is certified against"
        },
        threats=[
            "A lossy shim producing different behaviour on each branch",
            "An unclassified interface assumed compatible",
            "A component run on an uncertified branch",
            "Divergence growing unnoticed between releases"
        ],
        failure_modes=[
            "Interface unclassified",
            "Interface semantically divergent",
            "Component not certified for this branch",
            "Shim refused"
        ],
        slos=[
            Slo("no silent divergence", "zero components run on an uncertified branch", "no budget"),
            Slo("matrix completeness", "every interface in use is classified", "no budget"),
            Slo("drift visibility", "divergence count reported every release", "no budget")
        ],
        signals={
            "interfaces_classified": "gauge by classification",
            "shim_refusals": "counter by interface",
            "uncertified_runs": "counter, expected to stay at zero",
            "divergence_drift": "gauge of divergent interfaces per release"
        },
    )
