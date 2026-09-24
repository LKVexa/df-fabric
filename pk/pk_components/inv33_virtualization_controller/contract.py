"""Binding contract for INV-33 - Virtualization controller.

The virtualization controller is the node-local authority that turns a placement into a running guest and back again. It holds the lease: a guest exists because a lease says so, and when the lease expires without renewal the guest is reclaimed rather than orphaned.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-33"
ELEMENT_NAME = "Virtualization controller"


def build() -> Contract:
    """Return the production contract for INV-33."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own guest lifecycle against a renewable lease: admit a placement, start the guest, require lease renewal to keep it, and reclaim guests whose lease expired so no instance outlives the authority that created it."
        ),
        owns=[
            "The guest lease and its renewal",
            "Guest start, stop and reclaim",
            "Reconciliation between intended and actual guests",
            "Orphan detection and reclamation",
            "Refusal to start without a valid lease"
        ],
        not_owns=[
            "Placement decisions",
            "Isolation tier internals",
            "Resource adjustment",
            "Node lifecycle",
            "Capacity targets"
        ],
        dependencies=[
            Dependency("SCH-01 Workload classification and placement", "upstream", "Issues the placement lease this controller honours"),
            Dependency("PLN-04 Execution plane", "upstream", "Decides the tier the guest runs in"),
            Dependency("INV-24 MicroVM runtime", "downstream", "Starts and stops the actual instances"),
            Dependency("INV-32 Elastic virtualization", "downstream", "Adjusts resources for guests this controller owns"),
            Dependency("GAP-01 Edge Node Supervisor", "peer", "Drains these guests when the node leaves service")
        ],
        source_of_truth="The lease: a guest without a current lease is an orphan and is reclaimed, whatever the runtime reports.",
        assumptions=[
            "The control plane may be unreachable when a lease comes up for renewal",
            "A runtime may report a guest the controller never started",
            "Reclaiming a guest is always safe; leaving an orphan is not"
        ],
        boundaries={
            "tenant": "leases are per workload and carry the tenant",
            "environment": "lease durations differ per environment",
            "site": "the controller is authoritative for its node only",
            "workload": "one lease per guest instance"
        },
        mandatory=[
            "Refuse to start a guest without a valid lease",
            "Require renewal before the lease expires",
            "Reclaim guests whose lease has expired",
            "Detect and reclaim guests the controller did not start",
            "Reconcile intended against actual on every pass"
        ],
        optional=[
            "Grace period before reclaim",
            "Lease pre-renewal",
            "Soft-stop before hard reclaim"
        ],
        non_goals=[
            "Deciding placement",
            "Implementing runtimes",
            "Adjusting resources",
            "Keeping a guest alive past its lease because it looks healthy"
        ],
        interfaces={
            "lease": "PK_GUEST_LEASE/1 - grant and renew the authority for one guest",
            "reconcile": "PK_GUEST_RECONCILIATION/1 - intended versus actual, with actions taken"
        },
        threats=[
            "An orphaned guest surviving the control plane that created it",
            "Lease forgery keeping a guest alive indefinitely",
            "Reclaim suppression by a compromised runtime",
            "A runtime-reported guest the controller never authorised"
        ],
        failure_modes=[
            "Lease expired without renewal",
            "Runtime reports an unknown guest",
            "Start requested with no lease",
            "Control plane unreachable at renewal time"
        ],
        slos=[
            Slo("no orphans", "zero guests running without a current lease after a reconcile pass", "no budget"),
            Slo("lease enforcement", "zero guests started without a valid lease", "no budget"),
            Slo("reconcile latency", "p99 reconcile pass under 200ms for 500 guests", "1% may exceed")
        ],
        signals={
            "guests": "gauge by state and tenant",
            "lease_remaining": "gauge of ticks until each guest's lease expires",
            "reclaims": "counter by reason (expired, orphan, drain)",
            "reconcile_actions": "counter by action taken",
            "unknown_guests": "counter of runtime-reported guests with no lease"
        },
    )
