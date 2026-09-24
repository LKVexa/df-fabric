"""Binding contract for INV-51 - Example state stores.

Example state stores are the proof that the state contract is implementable more than one way. Two stores ship here -- an in-memory map and a file-backed journal -- and both are run through one conformance suite, so 'implements the state contract' is a test result rather than a claim.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-51"
ELEMENT_NAME = "Example state stores"


def build() -> Contract:
    """Return the production contract for INV-51."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the reference state stores and the conformance suite they, and any third-party store, must pass."
        ),
        owns=[
            "The in-memory reference store",
            "The file-backed journal store",
            "The shared conformance suite",
            "Durability behaviour of the file store across restart",
            "Reporting which contract checks a store passes"
        ],
        not_owns=[
            "The state contract itself",
            "Production database operation",
            "Replication",
            "Encryption at rest",
            "Adapter admission"
        ],
        dependencies=[
            Dependency("INV-50 State abstraction", "upstream", "Defines the contract these stores implement"),
            Dependency("INV-49 Pluggable infrastructure adapters", "downstream", "Admits these stores"),
            Dependency("GAP-15 Runtime compatibility certification", "downstream", "Uses the conformance suite as evidence"),
            Dependency("INV-57 Durable execution", "peer", "Persists workflow history through a store like these")
        ],
        source_of_truth="The conformance suite result; a store is conformant when it passes, whatever its documentation says.",
        assumptions=[
            "Every peer, network path and store can fail independently",
            "Callers are untrusted until their identity is established",
            "Behaviour must be identical whether a dependency is local or remote"
        ],
        boundaries={
            "tenant": "state and traffic are partitioned per tenant and never shared",
            "environment": "limits and endpoints differ per environment",
            "site": "each site runs its own instance; nothing assumes a global singleton",
            "workload": "budgets and quotas are per workload"
        },
        mandatory=[
            "Implement get, set and delete with etags in both stores",
            "Survive restart in the file store",
            "Run the same conformance suite against every store",
            "Report every failed check by name",
            "Never write a database file into a synced or mounted folder"
        ],
        optional=[
            "Batching where the protocol allows it",
            "Per-tenant tuning of limits",
            "Additional adapters"
        ],
        non_goals=[
            "Operating production databases",
            "Replicating",
            "Defining the contract"
        ],
        interfaces={
            "store": "PK_STATE_STORE/1 - a reference store implementation",
            "conformance": "PK_STATE_CONFORMANCE/1 - the suite and its per-check results"
        },
        threats=[
            "A store that loses writes on restart",
            "A store that ignores etags",
            "Divergent behaviour between implementations"
        ],
        failure_modes=[
            "Conformance check failed",
            "Journal corrupt",
            "Journal unwritable",
            "Etag ignored"
        ],
        slos=[
            Slo("conformance", "every shipped store passes every check", "no budget"),
            Slo("durability", "file store loses zero acknowledged writes across restart", "no budget"),
            Slo("suite time", "full conformance suite under 1s per store", "none may exceed 5s")
        ],
        signals={
            "checks_passed": "gauge by store",
            "checks_failed": "counter by check",
            "journal_bytes": "gauge"
        },
    )
