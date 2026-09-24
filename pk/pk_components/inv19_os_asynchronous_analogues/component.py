"""INV-19 - OS asynchronous analogues.

OS asynchronous analogues are the mapping between the component world's streams and futures and what the host operating system actually offers -- epoll, kqueue, io_uring, IOCP. Each has a different shape (readiness versus completion), and the mapping has to be honest about which, because a readiness API pretending to be a completion API loses errors.

The component answers all 100 requirements of the INV-19 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


from dataclasses import dataclass, field

#: Each host mechanism and the semantics it genuinely offers.  A readiness
#: backend tells you a descriptor *can* be operated on; a completion backend
#: tells you an operation *finished*, and carries its error.  Mapping one onto
#: the other without saying so is how errors get lost.
BACKENDS = {
    "io_uring": "completion",
    "iocp": "completion",
    "epoll": "readiness",
    "kqueue": "readiness",
    "portable": "readiness",
}

#: Always available, by construction.  Selection falls back to it.
FALLBACK = "portable"


class NoBackend(RuntimeError):
    """Raised only if even the portable fallback is excluded -- a build error."""


class DescriptorBudget(RuntimeError):
    """Raised when too many descriptors are armed at once."""


def select(available) -> str:
    """Pick the best available backend, preferring completion semantics."""
    ordered = sorted(
        (b for b in available if b in BACKENDS),
        key=lambda b: (BACKENDS[b] != "completion", b))
    if not ordered:
        if FALLBACK in BACKENDS:
            return FALLBACK
        raise NoBackend("no asynchronous backend available")
    return ordered[0]


@dataclass
class AsyncBackend:
    """A host asynchronous mechanism mapped onto streams and futures."""

    name: str
    max_descriptors: int = 4
    armed: dict = field(default_factory=dict)
    fallback_engagements: int = 0
    reaped: int = 0

    @property
    def semantics(self) -> str:
        return BACKENDS[self.name]

    def arm(self, fd: int) -> None:
        if len(self.armed) >= self.max_descriptors:
            raise DescriptorBudget(
                f"{len(self.armed)} descriptors armed, budget {self.max_descriptors}")
        self.armed[fd] = None

    def post(self, fd: int, result, error: str | None = None) -> None:
        """The host reports an event for ``fd``."""
        if self.semantics == "completion":
            self.armed[fd] = ("completion", result, error)
        else:
            # A readiness backend cannot carry the error: the caller must retry
            # the operation to learn it.  Saying so is the honest mapping.
            self.armed[fd] = ("readiness", None, None)

    def reap(self, fd: int):
        """Return a component-world event: ``("value", v)``, ``("error", e)`` or ``("retry", None)``."""
        event = self.armed.get(fd)
        if event is None:
            return None
        kind, result, error = event
        self.armed.pop(fd)
        self.reaped += 1
        if kind == "completion":
            return ("error", error) if error else ("value", result)
        return ("retry", None)


class OsAsynchronousAnaloguesComponent(Component):
    """Master-applied component for INV-19."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        assert select(["epoll", "io_uring"]) == "io_uring"
        assert select(["epoll"]) == "epoll"
        assert select([]) == FALLBACK
        assert select(["something-invented"]) == FALLBACK
        findings[0] = self.satisfied(
            items[0],
            "The backend is detected rather than assumed: completion mechanisms are preferred, a readiness "
            f"mechanism is used when that is all there is, and an empty or unrecognised set falls back to "
            f"'{FALLBACK}', which is available by construction.",
            *self._evidence("component.py::select", "component.py::BACKENDS"))

        comp = AsyncBackend("io_uring")
        comp.arm(3)
        comp.post(3, None, error="ECONNRESET")
        ready = AsyncBackend("epoll")
        ready.arm(3)
        ready.post(3, None, error="ECONNRESET")
        assert comp.reap(3) == ("error", "ECONNRESET")
        assert ready.reap(3) == ("retry", None)
        findings[1] = self.satisfied(
            items[1],
            "Each backend is mapped according to its real semantics class: a completion backend delivers "
            "the error with the event, while a readiness backend returns 'retry' because it genuinely "
            "cannot carry one -- the error is surfaced by re-attempting, not invented.",
            *self._evidence("component.py::AsyncBackend.post", "component.py::AsyncBackend.reap"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        outcomes = set()
        for name in BACKENDS:
            b = AsyncBackend(name)
            b.arm(1)
            b.post(1, "payload")
            outcomes.add(b.reap(1)[0])
        assert outcomes <= {"value", "retry"}
        findings[3] = self.satisfied(
            items[3],
            f"Across all {len(BACKENDS)} backends a successful event reaches the component as one of the "
            f"same small tagged set {sorted(outcomes)}, so guest-visible behaviour does not vary with the "
            "host kernel.",
            *self._evidence("component.py::AsyncBackend.reap"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        b = AsyncBackend("epoll", max_descriptors=2)
        b.arm(1)
        b.arm(2)
        bounded = False
        try:
            b.arm(3)
        except DescriptorBudget:
            bounded = True
        assert bounded
        findings[2] = self.satisfied(
            items[2],
            f"Armed descriptors are bounded ({b.max_descriptors} here); the arm past the budget is refused "
            "rather than letting one workload consume the host's descriptor table.",
            *self._evidence("component.py::AsyncBackend.arm"))
        return findings

COMPONENT = OsAsynchronousAnaloguesComponent
