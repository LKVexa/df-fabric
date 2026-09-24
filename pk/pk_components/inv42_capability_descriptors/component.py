"""INV-42 - Capability descriptors.

Capability descriptors are what a reference becomes when it has to leave the process: a typed, serialized handle passed across an ABI boundary. Serialization is exactly where authority usually leaks, so this element makes a descriptor useless outside the table it belongs to.

The component answers all 100 requirements of the INV-42 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import secrets
from dataclasses import dataclass, field

#: Maximum live descriptors per table.
TABLE_LIMIT = 1024


class ForeignDescriptor(PermissionError):
    """Raised when a descriptor is presented to a table that did not issue it."""


class DescriptorClosed(PermissionError):
    """Raised when a closed descriptor number is used again."""


class TypeMismatch(TypeError):
    """Raised when a descriptor is resolved as the wrong resource type."""


@dataclass(frozen=True)
class Descriptor:
    """A serialized capability: a number that only means something in its own table."""

    number: int
    resource_type: str
    table_id: str

    def to_wire(self) -> dict:
        return {"schema": "PK_DESCRIPTOR/1", "number": self.number,
                "type": self.resource_type, "table": self.table_id}


@dataclass
class DescriptorTable:
    """One workload's descriptor table. Numbers are never reused within it."""

    owner: str
    table_id: str = field(default_factory=lambda: secrets.token_hex(8))
    _next: int = 3                       # 0,1,2 reserved, as on a real ABI
    entries: dict = field(default_factory=dict)      # number -> (type, resource)
    closed: set = field(default_factory=set)

    def open(self, resource_type: str, resource) -> Descriptor:
        if len(self.entries) >= TABLE_LIMIT:
            raise RuntimeError(f"{self.owner}: descriptor table is full ({TABLE_LIMIT})")
        number, self._next = self._next, self._next + 1   # monotonic: never reused
        self.entries[number] = (resource_type, resource)
        return Descriptor(number, resource_type, self.table_id)

    def resolve(self, descriptor: Descriptor, *, expect: str | None = None):
        if descriptor.table_id != self.table_id:
            raise ForeignDescriptor(
                f"{self.owner}: descriptor {descriptor.number} belongs to another table")
        if descriptor.number in self.closed:
            raise DescriptorClosed(
                f"{self.owner}: descriptor {descriptor.number} was closed")
        entry = self.entries.get(descriptor.number)
        if entry is None:
            raise ForeignDescriptor(
                f"{self.owner}: descriptor {descriptor.number} is not allocated here")
        resource_type, resource = entry
        if expect is not None and resource_type != expect:
            raise TypeMismatch(
                f"descriptor {descriptor.number} is {resource_type!r}, resolved as {expect!r}")
        return resource

    def close(self, descriptor: Descriptor) -> dict:
        self.resolve(descriptor)          # closing a foreign descriptor is also refused
        self.entries.pop(descriptor.number, None)
        self.closed.add(descriptor.number)
        return {"schema": "PK_DESCRIPTOR_CLOSE/1", "number": descriptor.number,
                "closed": True, "number_reusable": False}


class CapabilityDescriptorsComponent(Component):
    """Master-applied component for INV-42."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        table = DescriptorTable("w1")
        fd = table.open("stream", object())
        assert table.resolve(fd, expect="stream") is not None
        wire = fd.to_wire()
        assert wire["number"] == fd.number and wire["table"] == table.table_id
        findings[5] = self.satisfied(
            items[5],
            "A descriptor serializes to a number, a type and its owning table id -- the table binding "
            "travels with it rather than being implied by context.",
            *self._evidence("component.py::Descriptor.to_wire"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        mine, theirs = DescriptorTable("w1"), DescriptorTable("w2")
        fd = theirs.open("stream", object())
        try:
            mine.resolve(fd)
        except ForeignDescriptor:
            findings[5] = self.satisfied(
                items[5],
                "A descriptor issued by another workload's table is refused, so a guessed or stolen number "
                "resolves to nothing outside the table that created it.",
                *self._evidence("component.py::DescriptorTable.resolve"))
        table = DescriptorTable("w3")
        first = table.open("stream", "A")
        table.close(first)
        second = table.open("socket", "B")
        assert second.number != first.number
        try:
            table.resolve(first)
        except DescriptorClosed:
            findings[6] = self.satisfied(
                items[6],
                f"Numbers are monotonic and never reused: closing {first.number} did not free it for the "
                f"next allocation ({second.number}), so a stale descriptor cannot alias a new resource.",
                *self._evidence("component.py::DescriptorTable.open"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        table = DescriptorTable("w1")
        fd = table.open("stream", object())
        try:
            table.resolve(fd, expect="socket")
        except TypeMismatch:
            findings[6] = self.satisfied(
                items[6],
                "Resolving a stream descriptor as a socket raises rather than returning the wrong "
                "resource, so type confusion across the ABI boundary is caught at the boundary.",
                *self._evidence("component.py::DescriptorTable.resolve"))
        return findings

COMPONENT = CapabilityDescriptorsComponent
