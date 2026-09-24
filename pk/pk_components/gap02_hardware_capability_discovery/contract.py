"""Binding contract for GAP-02 - Hardware capability discovery.

Hardware capability discovery is what makes the rest of the estate honest about heterogeneity. It reports only what it has actually probed, distinguishes a capability that is absent from one it could not test, and never lets a node advertise more than it proved.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-02"
ELEMENT_NAME = "Hardware capability discovery"


def build() -> Contract:
    """Return the production contract for GAP-02."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Probe and publish the node's real hardware capabilities -- isolation primitives, accelerators, instruction-set extensions, secure elements -- as a signed, timestamped report in which unprobed is never reported as present."
        ),
        owns=[
            "Capability probing and its result states",
            "The node capability report and its freshness",
            "Separation of absent from unprobed",
            "Re-probe scheduling",
            "Refusal to advertise unproven capability"
        ],
        not_owns=[
            "Scheduling or placement",
            "Attestation of node identity",
            "Tier admission",
            "Accelerator allocation",
            "Firmware or driver management"
        ],
        dependencies=[
            Dependency("GAP-06 Device identity and attestation", "upstream", "Signs the capability report with the node's identity"),
            Dependency("SCH-01 Workload classification and placement", "downstream", "Filters candidates on the reported capabilities"),
            Dependency("PLN-04 Execution plane", "downstream", "Builds its tier catalogue from the reported isolation primitives"),
            Dependency("GAP-11 Accelerator scheduling", "downstream", "Allocates only accelerators this report proved"),
            Dependency("GAP-01 Edge Node Supervisor", "peer", "Publishes the report as part of node readiness")
        ],
        source_of_truth="The probe result itself; a capability with no successful probe does not exist for scheduling purposes.",
        assumptions=[
            "Probes may be unavailable in a container or under a restricted kernel",
            "Hardware may be hot-added or fail between probes",
            "A probe may be expensive enough that it cannot run on every report"
        ],
        boundaries={
            "tenant": "capability reports are node-level and carry no tenant data",
            "environment": "an environment may require a minimum capability floor",
            "site": "sites differ in hardware and the report must not be normalised across them",
            "workload": "workload requirements are matched against the report, never the reverse"
        },
        mandatory=[
            "Probe each declared capability and record present, absent, or unprobed",
            "Never report unprobed as present",
            "Timestamp every report and expose its freshness",
            "Re-probe on a bounded schedule and on hot-add",
            "Refuse to publish a report that fails its own consistency check"
        ],
        optional=[
            "Deep accelerator benchmarking",
            "Firmware version reporting",
            "Probe result caching across reboots"
        ],
        non_goals=[
            "Making placement decisions",
            "Attesting node identity",
            "Installing drivers",
            "Inferring a capability from a sibling node"
        ],
        interfaces={
            "probe": "PK_CAPABILITY_PROBE/1 - run and record one capability probe",
            "report": "PK_NODE_CAPABILITIES/1 - the node's signed capability report with freshness",
            "schedule": "PK_PROBE_SCHEDULE/1 - which probes run when"
        },
        threats=[
            "A node over-reporting capability to attract workloads",
            "Probe spoofing by a compromised local agent",
            "Stale report used after hardware failure",
            "Capability downgrade attack removing an isolation primitive silently"
        ],
        failure_modes=[
            "Probe cannot run in this environment",
            "Hardware disappears between probes",
            "Report is older than its freshness bound",
            "Probe returns an ambiguous result"
        ],
        slos=[
            Slo("report soundness", "zero capabilities reported present without a successful probe", "no budget"),
            Slo("freshness", "99% of consumed reports younger than the freshness bound", "1% may be refused as stale"),
            Slo("probe cost", "full probe sweep under 5s on a constrained edge node", "5% may exceed on first boot")
        ],
        signals={
            "capability_state": "per capability: present, absent, or unprobed",
            "report_age_seconds": "gauge of the current report's age",
            "probe_failures": "counter by capability and reason",
            "capability_changes": "counter of transitions between probe results"
        },
    )
