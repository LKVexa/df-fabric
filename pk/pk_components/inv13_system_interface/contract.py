"""Binding contract for INV-13 - System interface.

The system interface is WASI: the component's only door to the outside world. Nothing is ambient -- no implicit filesystem, no implicit clock, no implicit network. A component gets exactly the preopened handles its world declared, and asks for anything else in vain.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-13"
ELEMENT_NAME = "System interface"


def build() -> Contract:
    """Return the production contract for INV-13."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the host-interface surface a component sees: grant only the capabilities its declared world lists, resolve every path against a preopened directory, and refuse any request for a resource the component was not given."
        ),
        owns=[
            "The world declaration a component is instantiated against",
            "Preopened handle tables",
            "Path resolution confined to preopens",
            "Refusal of undeclared capability requests",
            "Clock and randomness capability gating"
        ],
        not_owns=[
            "Host implementations behind the interface",
            "Interface type definitions",
            "The canonical ABI",
            "Composition linking",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-42 Capability descriptors", "upstream", "Supplies the descriptor table preopens live in"),
            Dependency("INV-11 Interface contract language", "upstream", "Types the system interfaces"),
            Dependency("INV-22 Alternative WASI branch", "peer", "A different branch of the same interface family"),
            Dependency("INV-20 HTTP component worlds", "downstream", "Builds an HTTP world on this interface")
        ],
        source_of_truth="The component's declared world plus its preopens; anything outside both does not exist for that component.",
        assumptions=[
            "A component will request whatever it can reach",
            "Path traversal is the oldest confinement bypass there is",
            "Ambient authority reappears wherever a default is provided"
        ],
        boundaries={
            "tenant": "preopens never span tenants",
            "environment": "worlds differ per environment",
            "site": "a site may lack a capability a world declares",
            "workload": "one world per component instance"
        },
        mandatory=[
            "Instantiate a component only against a declared world",
            "Grant only the capabilities the world lists",
            "Resolve every path against a preopened directory",
            "Refuse path escapes from a preopen",
            "Provide no default or ambient capability"
        ],
        optional=[
            "Read-only preopens",
            "Clock resolution limiting",
            "Deterministic randomness for replay"
        ],
        non_goals=[
            "Implementing filesystems or networks",
            "Providing a default environment",
            "Resolving absolute paths",
            "Granting a capability because it seems harmless"
        ],
        interfaces={
            "world": "PK_WORLD/1 - the capabilities a component is instantiated with",
            "preopen": "PK_PREOPEN/1 - a granted directory handle and its root",
            "resolve": "PK_PATH_RESOLVE/1 - a path resolved within a preopen"
        },
        threats=[
            "Path traversal escaping a preopened directory",
            "A component obtaining a clock it was not granted and using it as a side channel",
            "Absolute paths reaching the host filesystem",
            "Capability creep through a permissive default world"
        ],
        failure_modes=[
            "Capability not in the world",
            "Path escapes its preopen",
            "Absolute path supplied",
            "No preopen for the requested root"
        ],
        slos=[
            Slo("confinement", "zero paths resolved outside a preopen", "no budget"),
            Slo("no ambient", "zero capabilities granted that the world did not declare", "no budget"),
            Slo("resolve latency", "p99 under 1us per path", "1% may exceed")
        ],
        signals={
            "world_instantiations": "counter by world and outcome",
            "capability_denials": "counter by capability",
            "path_escapes": "counter of refused traversals",
            "preopens": "gauge per component instance"
        },
    )
