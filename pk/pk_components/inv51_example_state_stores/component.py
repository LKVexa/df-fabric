"""INV-51 - Example state stores.

Example state stores are the proof that the state contract is implementable more than one way. Two stores ship here -- an in-memory map and a file-backed journal -- and both are run through one conformance suite, so 'implements the state contract' is a test result rather than a claim.

The component answers all 100 requirements of the INV-51 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


import json
import os
import tempfile
from pathlib import Path


class Conflict(RuntimeError):
    pass


class MemoryStore:
    def __init__(self):
        self.d, self.n = {}, 0

    def get(self, k):
        return self.d.get(k, (None, None))

    def set(self, k, v, etag=None):
        cur = self.d.get(k, (None, None))[1]
        if etag is not None and etag != cur:
            raise Conflict(k)
        self.n += 1
        self.d[k] = (v, self.n)
        return self.n

    def delete(self, k):
        self.d.pop(k, None)


class JournalStore(MemoryStore):
    """Append-only JSON-lines journal replayed on open.  Plain files, never a database."""

    def __init__(self, path: Path):
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec["op"] == "set":
                    self.d[rec["k"]] = (rec["v"], rec["etag"])
                    self.n = max(self.n, rec["etag"])
                else:
                    self.d.pop(rec["k"], None)

    def _append(self, rec):
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def set(self, k, v, etag=None):
        n = super().set(k, v, etag)
        self._append({"op": "set", "k": k, "v": v, "etag": n})
        return n

    def delete(self, k):
        super().delete(k)
        self._append({"op": "delete", "k": k})


def conformance(make) -> dict:
    """The one suite every store runs.  Returns {check: passed}."""
    results = {}
    s = make()
    s.set("a", 1)
    results["read-your-write"] = s.get("a")[0] == 1
    _, e = s.get("a")
    s.set("a", 2, etag=e)
    try:
        s.set("a", 3, etag=e)
        results["stale-etag-refused"] = False
    except Conflict:
        results["stale-etag-refused"] = True
    s.delete("a")
    results["delete"] = s.get("a") == (None, None)
    results["etag-advances"] = s.set("b", 1) != s.set("b", 2)
    return results


def scratch_journal() -> Path:
    return Path(tempfile.mkdtemp(prefix="pk-inv51-")) / "state.jsonl"


class ExampleStateStoresComponent(Component):
    """Master-applied component for INV-51."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        path = scratch_journal()
        mem = conformance(MemoryStore)
        jour = conformance(lambda: JournalStore(scratch_journal()))
        assert all(mem.values()) and mem == jour
        findings[0] = self.satisfied(
            items[0],
            f"Both reference stores pass the same {len(mem)}-check conformance suite "
            f"({', '.join(sorted(mem))}) with identical results, so the contract is demonstrably "
            "implementable two ways.",
            *self._evidence("component.py::conformance"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        path = scratch_journal()
        s = JournalStore(path)
        s.set("order", "paid")
        s.set("gone", 1)
        s.delete("gone")
        reopened = JournalStore(path)
        assert reopened.get("order")[0] == "paid" and reopened.get("gone") == (None, None)
        assert reopened.set("x", 1) > s.get("order")[1]
        findings[0] = self.satisfied(
            items[0],
            "The file store fsyncs each journal record and replays it on reopen: an acknowledged write "
            "and a delete both survive a restart, and etags keep advancing rather than resetting.",
            *self._evidence("component.py::JournalStore"))
        return findings

COMPONENT = ExampleStateStoresComponent
