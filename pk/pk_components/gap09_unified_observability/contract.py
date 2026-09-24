"""Binding contract for GAP-09 - Unified observability.

Unified observability is the estate's evidence layer. Every signal is attributed to the workload and tenant that produced it, signed by the node that reported it, and carries its own staleness -- so a missing signal reads as missing rather than as zero.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-09"
ELEMENT_NAME = "Unified observability"


def build() -> Contract:
    """Return the production contract for GAP-09."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own signal ingestion and attribution: accept only signals signed by an attested reporter, attribute each to its tenant, site and workload, and expose staleness so absence is never mistaken for a healthy zero."
        ),
        owns=[
            "Signal ingestion and reporter authentication",
            "Tenant/site/workload attribution",
            "Staleness tracking per signal",
            "Cross-tenant query isolation",
            "The distinction between zero and absent"
        ],
        not_owns=[
            "What the signals mean to a consumer",
            "Alerting policy",
            "Long-term storage",
            "Node health decisions",
            "Capacity decisions"
        ],
        dependencies=[
            Dependency("GAP-06 Device identity and attestation", "upstream", "Attests the reporters whose signals are accepted"),
            Dependency("GAP-07 Artifact provenance/signing", "upstream", "Verifies reporter signatures"),
            Dependency("GAP-01 Edge Node Supervisor", "downstream", "Aggregates node health from these signals"),
            Dependency("PLN-05 Elasticity plane", "downstream", "Takes demand samples from here"),
            Dependency("GAP-08 OTA lifecycle/rollback", "downstream", "Gates rollout waves on these signals")
        ],
        source_of_truth="The signed reporter submission; an unsigned or unattested submission is not evidence.",
        assumptions=[
            "A reporter may go silent without the underlying thing being healthy",
            "Signals arrive out of order and late from disconnected sites",
            "A consumer may ask for a signal that has never been reported"
        ],
        boundaries={
            "tenant": "a query may never return another tenant's signals",
            "environment": "signals are scoped per environment",
            "site": "site is a required attribution dimension",
            "workload": "every workload-level signal names its workload"
        },
        mandatory=[
            "Accept signals only from an attested, signed reporter",
            "Attribute every signal to tenant, site and workload",
            "Expose staleness alongside every value",
            "Return absent rather than zero for a signal never reported",
            "Refuse cross-tenant queries"
        ],
        optional=[
            "Downsampling and rollups",
            "Exemplar traces attached to metrics",
            "Local buffering during partition"
        ],
        non_goals=[
            "Deciding node health",
            "Alerting",
            "Long-term retention",
            "Inferring a value for a signal that was never reported"
        ],
        interfaces={
            "submit": "PK_SIGNAL_SUBMISSION/1 - signed batch of signals from one reporter",
            "query": "PK_SIGNAL_QUERY/1 - tenant-scoped read with staleness",
            "catalogue": "PK_SIGNAL_CATALOGUE/1 - declared signals, their meaning and unit"
        },
        threats=[
            "A forged reporter injecting demand to drive scaling or billing",
            "Cross-tenant signal leakage through a crafted query",
            "Signal suppression to mask a failing node",
            "Attribution stripping to make a signal unaccountable"
        ],
        failure_modes=[
            "Reporter is not attested",
            "Signal arrives late and out of order",
            "Queried signal has never been reported",
            "Reporter goes silent"
        ],
        slos=[
            Slo("attribution", "zero signals stored without tenant, site and workload", "no budget"),
            Slo("isolation", "zero queries returning another tenant's signals", "no budget"),
            Slo("absence fidelity", "zero unreported signals returned as a numeric zero", "no budget")
        ],
        signals={
            "ingested_signals": "counter by reporter and outcome",
            "rejected_submissions": "counter by reason (unattested, unsigned, unattributed)",
            "signal_staleness_seconds": "gauge per signal and reporter",
            "silent_reporters": "gauge of attested reporters with no recent submission",
            "cross_tenant_denials": "counter of queries refused for scope"
        },
    )
