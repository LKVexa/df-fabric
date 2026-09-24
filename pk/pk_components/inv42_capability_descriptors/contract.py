"""Binding contract for INV-42 - Capability descriptors.

Capability descriptors are what a reference becomes when it has to leave the process: a typed, serialized handle passed across an ABI boundary. Serialization is exactly where authority usually leaks, so this element makes a descriptor useless outside the table it belongs to.
"""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "INV-42"
ELEMENT_NAME = "Capability descriptors"


def build() -> Contract:
    """Return the production contract for INV-42."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own descriptor tables and the serialized form of a capability: bind every descriptor to its owning table, keep numbering non-reusable within a session, and refuse any descriptor presented to a table that did not issue it."
        ),
        owns=[
            "Per-process descriptor tables",
            "Descriptor allocation and closure",
            "Table binding of every descriptor",
            "Non-reuse of descriptor numbers within a session",
            "Typed transfer of descriptors across a boundary"
        ],
        not_owns=[
            "The underlying resources",
            "In-process reference semantics",
            "Wire protocols",
            "Policy authorship",
            "Placement"
        ],
        dependencies=[
            Dependency("INV-41 Capability security", "upstream", "Supplies the in-process references descriptors serialize"),
            Dependency("INV-13 System interface", "downstream", "Consumes descriptors at the system-interface boundary", required=False),
            Dependency("INV-11 Interface contract language", "peer", "Types the descriptor as it crosses an interface", required=False),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Passes descriptors to capability adapters")
        ],
        source_of_truth="The issuing table: a descriptor number means nothing except in the table that allocated it.",
        assumptions=[
            "Descriptor numbers are small integers and trivially guessable",
            "A closed descriptor number could otherwise be reallocated to a different resource",
            "Descriptors cross ABI boundaries where types are easily confused"
        ],
        boundaries={
            "tenant": "a descriptor table belongs to one workload of one tenant",
            "environment": "table size limits differ per environment",
            "site": "descriptors do not travel between sites as numbers",
            "workload": "one table per workload instance"
        },
        mandatory=[
            "Bind every descriptor to the table that issued it",
            "Refuse a descriptor presented to a foreign table",
            "Never reuse a descriptor number within a session",
            "Carry the resource type with the descriptor",
            "Make closure permanent for that number"
        ],
        optional=[
            "Descriptor transfer between tables under policy",
            "Table compaction across sessions",
            "Descriptor-use auditing"
        ],
        non_goals=[
            "Implementing resources",
            "Cross-process number portability",
            "Reusing numbers for compactness",
            "Trusting a descriptor number on its own"
        ],
        interfaces={
            "open": "PK_DESCRIPTOR/1 - allocate a typed descriptor in a table",
            "resolve": "PK_DESCRIPTOR_RESOLVE/1 - resolve a descriptor within its own table",
            "close": "PK_DESCRIPTOR_CLOSE/1 - permanently close a descriptor number"
        },
        threats=[
            "Descriptor number guessing reaching another resource",
            "Confused deputy: a descriptor resolved in the wrong table",
            "Number reuse after close aliasing a new resource",
            "Type confusion across an ABI boundary"
        ],
        failure_modes=[
            "Descriptor not in this table",
            "Descriptor already closed",
            "Type mismatch on resolution",
            "Table at its size limit"
        ],
        slos=[
            Slo("table binding", "zero descriptors resolved in a table that did not issue them", "no budget"),
            Slo("non-reuse", "zero descriptor numbers reused within a session", "no budget"),
            Slo("type fidelity", "zero descriptors resolved as the wrong type", "no budget")
        ],
        signals={
            "descriptors_open": "gauge per table",
            "foreign_resolutions": "counter of descriptors presented to the wrong table",
            "closed_reuse_attempts": "counter of uses after close",
            "type_mismatches": "counter by expected and actual type"
        },
    )
