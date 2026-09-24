"""Binding contract for GAP-15 - Runtime compatibility certification.

Runtime compatibility certification answers the question a heterogeneous edge estate asks constantly: will this artifact actually run on that node? It certifies against a declared matrix and refuses to guess, because an untested pair is not a supported pair.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-15"
ELEMENT_NAME = "Runtime compatibility certification"


def build() -> Contract:
    """Return the production contract for GAP-15."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the runtime compatibility matrix: certify an artifact against a runtime and node profile from tested evidence only, and return uncertified -- never a guess -- for a pair that has not been tested."
        ),
        owns=[
            "The compatibility matrix and its versioning",
            "Certification verdicts and their evidence",
            "The distinction between incompatible and untested",
            "Certification expiry",
            "Deprecation and end-of-life signalling for runtime versions"
        ],
        not_owns=[
            "Running the compatibility tests",
            "Building artifacts",
            "Rollout sequencing",
            "Node capability probing",
            "Runtime implementations"
        ],
        dependencies=[
            Dependency("GAP-02 Hardware capability discovery", "upstream", "Supplies the node profile certified against"),
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies the artifact whose compatibility is certified"),
            Dependency("GAP-08 OTA lifecycle/rollback", "downstream", "Refuses to roll out an uncertified bundle"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Places only onto certified runtime/node pairs"),
            Dependency("PLN-04 Execution plane", "downstream", "Admits only certified artifact/tier pairs")
        ],
        source_of_truth="The recorded test result for a specific (artifact, runtime, profile) triple; anything else is uncertified.",
        assumptions=[
            "The matrix is sparse: most triples have never been tested",
            "A certification goes stale as runtimes are patched",
            "A runtime version reaches end of life while still deployed"
        ],
        boundaries={
            "tenant": "certifications are estate-wide and not tenant-specific",
            "environment": "each environment certifies independently",
            "site": "sites with unusual hardware profiles need their own certification",
            "workload": "an artifact is certified, not a running workload"
        },
        mandatory=[
            "Certify only from a recorded test result",
            "Distinguish incompatible from untested",
            "Expire certifications and require re-testing",
            "Signal deprecated and end-of-life runtime versions",
            "Refuse to infer compatibility from a similar profile"
        ],
        optional=[
            "Profile similarity hints for prioritising testing",
            "Partial certification for feature subsets",
            "Automatic re-certification scheduling"
        ],
        non_goals=[
            "Running the tests",
            "Fixing incompatibilities",
            "Sequencing rollouts",
            "Guessing at an untested pair"
        ],
        interfaces={
            "matrix": "PK_COMPATIBILITY_MATRIX/1 - the tested triples and their results",
            "certify": "PK_CERTIFICATION/1 - verdict for one artifact/runtime/profile triple",
            "lifecycle": "PK_RUNTIME_LIFECYCLE/1 - supported, deprecated and end-of-life versions"
        },
        threats=[
            "Certification forgery admitting an untested artifact",
            "Matrix inference widening a narrow test result",
            "Expired certification reused during a rollout",
            "End-of-life runtime kept in service silently"
        ],
        failure_modes=[
            "Triple has never been tested",
            "Certification has expired",
            "Runtime version is end-of-life",
            "Test result contradicts an earlier one"
        ],
        slos=[
            Slo("no inference", "zero certified verdicts without a recorded test result", "no budget"),
            Slo("expiry", "zero expired certifications treated as current", "no budget"),
            Slo("eol enforcement", "zero rollouts certified onto an end-of-life runtime", "no budget")
        ],
        signals={
            "certifications": "counter by verdict (certified, incompatible, untested, expired)",
            "matrix_coverage": "gauge of tested triples over requested triples",
            "eol_runtimes_in_service": "gauge of nodes on end-of-life runtime versions",
            "certification_age_seconds": "gauge per certified triple"
        },
    )
