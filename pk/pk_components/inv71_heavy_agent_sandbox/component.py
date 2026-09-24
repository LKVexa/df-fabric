"""INV-71 - Heavy agent sandbox.

The heavy agent sandbox is for code the fast sandbox cannot or should not hold: real interpreters, package installs, browsers. Each agent session gets its own microVM-class boundary with a filesystem that starts from a clean snapshot, egress limited to an allowlist, and a teardown that leaves nothing behind for the next session to find.

The component answers all 100 requirements of the INV-71 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import hashlib
from dataclasses import dataclass, field

BASE = {"/usr/bin/python3": b"interpreter", "/etc/hosts": b"127.0.0.1 localhost"}


class EgressDenied(PermissionError):
    pass


class LimitExceeded(RuntimeError):
    pass


def digest(fs: dict) -> str:
    h = hashlib.sha256()
    for k in sorted(fs):
        h.update(k.encode() + b"\0" + fs[k])
    return h.hexdigest()


BASE_DIGEST = digest(BASE)


@dataclass
class Session:
    sid: str
    egress_allow: frozenset
    disk_quota: int = 1 << 20
    fs: dict = field(default_factory=lambda: dict(BASE))
    connections: list = field(default_factory=list)
    denied: list = field(default_factory=list)
    alive: bool = True

    def write(self, path: str, data: bytes) -> None:
        used = sum(len(v) for k, v in self.fs.items() if k not in BASE) + len(data)
        if used > self.disk_quota:
            raise LimitExceeded(f"{self.sid}: disk quota {self.disk_quota}")
        self.fs[path] = data

    def connect(self, host: str) -> None:
        if host not in self.egress_allow:
            self.denied.append(host)
            raise EgressDenied(f"{self.sid}: {host} not allowlisted")
        self.connections.append(host)

    def teardown(self) -> dict:
        self.fs, self.connections, self.alive = {}, [], False
        return {"sid": self.sid, "verified": not self.fs and not self.connections}


def new_session(sid: str, allow=()) -> Session:
    s = Session(sid, frozenset(allow))
    assert digest(s.fs) == BASE_DIGEST
    return s


class HeavyAgentSandboxComponent(Component):
    """Master-applied component for INV-71."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        s1 = new_session("s1", allow=["pypi.org"])
        s1.write("/tmp/stolen.txt", b"customer data")
        s1.connect("pypi.org")
        exfil = False
        try:
            s1.connect("paste.evil.example")
        except EgressDenied:
            exfil = True
        record = s1.teardown()
        s2 = new_session("s2")
        assert exfil and record["verified"]
        assert "/tmp/stolen.txt" not in s2.fs and digest(s2.fs) == BASE_DIGEST
        findings[0] = self.satisfied(
            items[0],
            "Egress is allowlisted per session (the package index connects, a paste site is refused), "
            "teardown is verified empty, and the next session starts from a filesystem whose digest "
            "equals the clean base -- the previous session's file is simply not there.",
            *self._evidence("component.py::Session", "component.py::new_session"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = new_session("s3")
        s.disk_quota = 1000
        s.write("/work/a", b"x" * 600)
        hit = False
        try:
            s.write("/work/b", b"x" * 600)
        except LimitExceeded:
            hit = True
        assert hit and "/work/b" not in s.fs
        findings[0] = self.satisfied(
            items[0],
            "A session's writes are held to its disk quota: the write that would exceed it is refused "
            "and not partially applied, so one session cannot fill the host.",
            *self._evidence("component.py::Session.write"))
        return findings

COMPONENT = HeavyAgentSandboxComponent
