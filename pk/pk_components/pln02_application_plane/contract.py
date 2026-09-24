"""Binding contract for PLN-02 - Application plane.

The application plane is where an application is described as a composition of components and the capabilities they require, rather than as a bag of containers and YAML. It resolves a composition against available capability providers and refuses to admit an application whose required capabilities cannot be satisfied.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "PLN-02"
ELEMENT_NAME = "Application plane"


def build() -> Contract:
    """Return the production contract for PLN-02."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the application model: resolve a declared composition of components and required capabilities into a satisfiable, versioned application revision, or reject it with the unsatisfied requirement named."
        ),
        owns=[
            "The application model and component composition graph",
            "Capability requirement resolution against providers",
            "Application revision identity and immutability",
            "Interface compatibility checks between composed components",
            "Rejection of unsatisfiable compositions"
        ],
        not_owns=[
            "Where a component runs",
            "The runtime that executes a component",
            "Capability provider implementations",
            "Network transport between components",
            "Desired state of the estate"
        ],
        dependencies=[
            Dependency("PLN-01 Intent plane", "upstream", "Receives the application declaration and its revision target"),
            Dependency("INV-65 Capability providers", "upstream", "The provider catalogue requirements resolve against"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Executes the resolved revision"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Classifies each resolved component"),
            Dependency("INV-11 Interface contract language", "peer", "Supplies the interface types compared during composition")
        ],
        source_of_truth="The immutable application revision produced by resolution; a revision is never edited, only superseded.",
        assumptions=[
            "Component interfaces are described in a typed contract language",
            "Provider catalogues are per-environment and may differ between sites",
            "A component may declare an optional capability that resolution is allowed to drop"
        ],
        boundaries={
            "tenant": "applications and their revisions are tenant-scoped",
            "environment": "resolution happens per environment against that environment's provider catalogue",
            "site": "site affinity is a requirement, not a placement decision",
            "workload": "a component is the unit of composition and of later placement"
        },
        mandatory=[
            "Resolve every required capability or reject the revision",
            "Verify interface compatibility across every composition edge",
            "Produce an immutable, content-addressed revision",
            "Record which provider satisfied each requirement",
            "Distinguish required from optional capabilities during resolution"
        ],
        optional=[
            "Automatic provider selection by cost or locality",
            "Partial revisions for preview environments",
            "Composition visualisation"
        ],
        non_goals=[
            "Scheduling or placement",
            "Running components",
            "Implementing capability providers",
            "Mutating an already-published revision"
        ],
        interfaces={
            "compose": "PK_APPLICATION/1 - declare components, edges, and capability requirements",
            "resolve": "PK_APPLICATION_REVISION/1 - immutable resolved revision with provider bindings",
            "catalogue": "PK_PROVIDER_CATALOGUE/1 - available capability providers for an environment"
        },
        threats=[
            "A component declaring a capability it is not entitled to",
            "Provider substitution between resolution and execution",
            "Interface type confusion across a composition edge",
            "Catalogue poisoning introducing a hostile provider",
            "Revision identity collision"
        ],
        failure_modes=[
            "A required capability has no provider in the environment",
            "Two composed components declare incompatible interface versions",
            "The provider catalogue is unavailable during resolution"
        ],
        slos=[
            Slo("resolution latency", "p99 resolution under 500ms for compositions up to 200 components", "1% may exceed"),
            Slo("revision immutability", "zero published revisions mutated after resolution", "no budget"),
            Slo("resolution soundness", "zero revisions published with an unsatisfied required capability", "no budget")
        ],
        signals={
            "application_revisions": "counter of published revisions per tenant",
            "resolution_rejections": "counter labelled by unsatisfied requirement",
            "resolution_seconds": "histogram of resolution latency",
            "provider_bindings": "gauge of active bindings per provider"
        },
    )
