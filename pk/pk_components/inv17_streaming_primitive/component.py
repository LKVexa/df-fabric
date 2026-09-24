"""INV-17 - Streaming primitive.

The streaming primitive carries many values over time through one typed handle. What makes it worth having as a primitive rather than a convention is that backpressure, end-of-stream and the reader's disappearance are all part of the type -- a writer that ignores a closed reader gets an error, not a silently discarded value.

The component answers all 100 requirements of the INV-17 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field


class CreditExhausted(RuntimeError):
    """Raised when a writer has no credit left; this is backpressure, not an error state."""


class EndDropped(RuntimeError):
    """Raised when the far end of a stream is gone."""


class ElementTypeMismatch(TypeError):
    """Raised when an element does not match the stream's declared type."""


@dataclass
class Stream:
    """A typed, credit-limited, explicitly-terminated stream of values.

    Credit is the whole design: a writer may only put as many elements on the
    stream as the reader has asked for, so a slow reader bounds memory rather
    than growing the buffer.
    """

    element_type: type
    credit: int = 0
    buffer: list = field(default_factory=list)
    ended: bool = False
    reader_dropped: bool = False
    writer_dropped: bool = False
    credit_stalls: int = 0
    transferred: int = 0

    def grant(self, n: int) -> None:
        """Reader-side: allow the writer ``n`` more elements."""
        if n <= 0:
            raise ValueError("credit must be positive")
        self.credit += n

    def write(self, element) -> None:
        if self.reader_dropped:
            raise EndDropped("reader end has been dropped")
        if self.ended:
            raise EndDropped("stream already ended")
        if not isinstance(element, self.element_type):
            raise ElementTypeMismatch(
                f"{type(element).__name__} on a stream of {self.element_type.__name__}")
        if self.credit <= 0:
            self.credit_stalls += 1
            raise CreditExhausted("no credit; reader has not asked for more")
        self.credit -= 1
        self.buffer.append(element)
        self.transferred += 1

    def read(self):
        """Return the next element, or ``None`` once the stream has ended."""
        if self.buffer:
            return self.buffer.pop(0)
        if self.writer_dropped:
            raise EndDropped("writer end has been dropped")
        if self.ended:
            return None
        return ...  # not ready yet; the caller waits on the ABI

    def end(self) -> None:
        """Explicit end-of-stream.  Silence is never end-of-stream."""
        self.ended = True

    def drop_reader(self) -> None:
        self.reader_dropped = True

    def drop_writer(self) -> None:
        self.writer_dropped = True


class StreamingPrimitiveComponent(Component):
    """Master-applied component for INV-17."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        s = Stream(str)
        s.grant(2)
        s.write("a")
        s.write("b")
        stalled = False
        try:
            s.write("c")
        except CreditExhausted:
            stalled = True
        assert stalled and len(s.buffer) == 2
        findings[0] = self.satisfied(
            items[0],
            f"The writer may only place as many elements as the reader granted ({len(s.buffer)} buffered "
            f"against 2 credit, {s.credit_stalls} stall); a slow reader bounds memory instead of growing "
            "the buffer.",
            *self._evidence("component.py::Stream.write"))

        typed = False
        s.grant(1)
        try:
            s.write(42)
        except ElementTypeMismatch:
            typed = True
        assert typed
        findings[1] = self.satisfied(
            items[1],
            "The element type is part of the stream, so a wrong-typed value is refused at the write rather "
            "than discovered by the reader.",
            *self._evidence("component.py::Stream.write"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = Stream(str)
        s.grant(1)
        s.drop_reader()
        errored = False
        try:
            s.write("a")
        except EndDropped:
            errored = True
        assert errored

        t = Stream(str)
        t.grant(1)
        t.write("a")
        t.end()
        assert t.read() == "a" and t.read() is None
        findings[1] = self.satisfied(
            items[1],
            "A write after the reader is dropped errors on the first attempt, and end-of-stream is an "
            "explicit signal the reader observes as None rather than an inference from silence.",
            *self._evidence("component.py::Stream.write", "component.py::Stream.end"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        s = Stream(int)
        peak = 0
        for i in range(100):
            s.grant(1)
            s.write(i)
            peak = max(peak, len(s.buffer))
            s.read()
        assert peak == 1 and s.transferred == 100
        findings[0] = self.satisfied(
            items[0],
            f"Over {s.transferred} elements with credit granted one at a time the in-flight buffer never "
            f"exceeded {peak} element, so memory is a function of granted credit and not of stream length.",
            *self._evidence("component.py::Stream"))
        return findings

COMPONENT = StreamingPrimitiveComponent
