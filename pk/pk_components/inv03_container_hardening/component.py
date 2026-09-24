"""INV-03 - Container hardening.

Container hardening is the list of things a container should not be allowed to do, checked before it runs: run as root, write to its own filesystem, keep Linux capabilities it never uses, run privileged, or skip a syscall filter. Each finding names the control that failed, and a workload only gets an exception if the exception is written down with an expiry date.

The component answers all 100 requirements of the INV-03 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


CONTROLS = {
    "non-root": lambda s: s.get("user", "root") not in ("root", "0"),
    "read-only-root": lambda s: s.get("readOnlyRootFilesystem") is True,
    "not-privileged": lambda s: not s.get("privileged"),
    "drop-all-capabilities": lambda s: "ALL" in s.get("capabilities", {}).get("drop", []),
    "seccomp": lambda s: s.get("seccomp") in ("RuntimeDefault", "Localhost"),
}


def evaluate(workload: str, spec: dict, exceptions: dict, today: int) -> dict:
    failed, excepted = [], []
    for name, check in CONTROLS.items():
        if check(spec):
            continue
        exc = exceptions.get((workload, name))
        if exc and exc["expires"] > today and exc.get("reason"):
            excepted.append(name)
        else:
            failed.append(name)
    return {"workload": workload, "admit": not failed, "failed": failed, "excepted": excepted}


class ContainerHardeningComponent(Component):
    """Master-applied component for INV-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        hard = {"user": "10001", "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]},
                "seccomp": "RuntimeDefault"}
        soft = {"privileged": True}
        assert evaluate("api", hard, {}, 100)["admit"]
        bad = evaluate("legacy", soft, {}, 100)
        assert not bad["admit"] and len(bad["failed"]) == len(CONTROLS)
        findings[0] = self.satisfied(
            items[0],
            f"A hardened spec passes all {len(CONTROLS)} controls; a privileged root container is "
            f"refused with every failed control named ({', '.join(bad['failed'])}).",
            *self._evidence("component.py::evaluate", "component.py::CONTROLS"))

        spec = dict(hard, readOnlyRootFilesystem=False)
        exc = {("cache", "read-only-root"): {"reason": "writes spool, ticket OPS-12", "expires": 200}}
        assert evaluate("cache", spec, exc, 150)["admit"]
        assert not evaluate("cache", spec, exc, 201)["admit"]
        assert not evaluate("cache", spec, {("cache", "read-only-root"): {"expires": 999}}, 150)["admit"]
        findings[1] = self.satisfied(
            items[1],
            "An exception works only if it is recorded with a reason and has not expired: the same "
            "workload is admitted before the expiry, refused after it, and refused if no reason was given.",
            *self._evidence("component.py::evaluate"))
        return findings

COMPONENT = ContainerHardeningComponent
