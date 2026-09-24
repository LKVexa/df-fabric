"""Binding contract for INV-26 - MicroVM snapshotting.

MicroVM snapshotting is what turns a hundred-millisecond cold boot into a few milliseconds, and it is also the easiest way to leak one tenant's memory into another's process. This element treats a snapshot as tenant-bound, entropy-poisoned material: restoring one into a different tenant is refused, and every restored guest is re-seeded.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-26"
ELEMENT_NAME = "MicroVM snapshotting"


def build() -> Contract:
    """Return the production contract for INV-26."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own snapshot capture and restore: bind every snapshot to its originating tenant and device model, refuse a cross-tenant or model-mismatched restore, and re-seed guest entropy on every restore so clones do not share randomness."
        ),
        owns=[
            "Snapshot capture and its metadata",
            "Tenant binding of snapshot material",
            "Device-model compatibility checking on restore",
            "Entropy re-seeding after restore",
            "Restore-time budget and its measurement"
        ],
        not_owns=[
            "MicroVM lifecycle",
            "Device definitions",
            "Storage of snapshot blobs",
            "Guest application state semantics",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-24 MicroVM runtime", "upstream", "Provides the instance being captured and restored"),
            Dependency("INV-25 MicroVM devices", "upstream", "Defines the device model a snapshot is bound to"),
            Dependency("PLN-05 Elasticity plane", "downstream", "Cold-start budget depends on restore time"),
            Dependency("GAP-07 Artifact provenance/signing", "peer", "Signs snapshots so a restored image is verifiable", required=False)
        ],
        source_of_truth="The snapshot's recorded tenant and device-model fingerprint; a restore that disagrees with either is refused.",
        assumptions=[
            "A snapshot contains live guest memory including secrets and RNG state",
            "Two guests restored from one snapshot start with identical entropy",
            "The device model may change between capture and restore"
        ],
        boundaries={
            "tenant": "a snapshot may only ever be restored into its originating tenant",
            "environment": "snapshots do not cross environments",
            "site": "a site may restore only snapshots whose device model it supports",
            "workload": "a snapshot belongs to the workload that produced it"
        },
        mandatory=[
            "Bind every snapshot to its tenant at capture",
            "Refuse a restore into a different tenant",
            "Refuse a restore when the device model fingerprint differs",
            "Re-seed guest entropy on every restore",
            "Measure restore time and report it against the cold-boot baseline"
        ],
        optional=[
            "Differential snapshots",
            "Snapshot compression",
            "Pre-warmed restore pools within one tenant"
        ],
        non_goals=[
            "Live migration",
            "Cross-tenant template sharing",
            "Storing snapshot blobs",
            "Guaranteeing application-level correctness after restore"
        ],
        interfaces={
            "capture": "PK_SNAPSHOT/1 - capture an instance with its tenant and model fingerprint",
            "restore": "PK_SNAPSHOT_RESTORE/1 - restore result with elapsed time and re-seed proof"
        },
        threats=[
            "Cross-tenant restore leaking guest memory",
            "Identical RNG state across clones breaking cryptography",
            "Device-model mismatch corrupting the restored guest",
            "Snapshot tampering between capture and restore"
        ],
        failure_modes=[
            "Tenant mismatch on restore",
            "Device-model fingerprint differs",
            "Snapshot blob missing or truncated",
            "Restore exceeds its budget"
        ],
        slos=[
            Slo("tenant binding", "zero cross-tenant restores", "no budget"),
            Slo("entropy", "zero restores without a re-seed", "no budget"),
            Slo("restore time", "p99 restore under 10ms, an order faster than cold boot", "1% may exceed")
        ],
        signals={
            "snapshots_captured": "counter by tenant and device model",
            "restore_seconds": "histogram of restore time against the cold-boot baseline",
            "cross_tenant_refusals": "counter of refused restores",
            "model_mismatches": "counter of refused restores by fingerprint",
            "reseeds": "counter of entropy re-seeds performed"
        },
    )
