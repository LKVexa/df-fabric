"""INV-67 - Kubernetes integration mechanism.

The Kubernetes integration mechanism lets existing manifests and tooling drive the new runtime during migration. It translates the supported subset of a pod spec into a runtime placement request -- and is loud about the rest: a privileged container or a hostPath mount is refused with the field named, never silently dropped into a workload that then behaves differently.

The component answers all 100 requirements of the INV-67 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


UNSUPPORTED = {
    ("securityContext", "privileged"): "privileged containers",
    ("volumes", "hostPath"): "host path mounts",
    ("spec", "hostNetwork"): "host networking",
    ("spec", "hostPID"): "host PID namespace",
}

PHASES = {"pending": "Pending", "running": "Running", "exited-0": "Succeeded", "failed": "Failed"}


class Unsupported(ValueError):
    pass


def quantity(q: str) -> float:
    if q.endswith("m"):
        return int(q[:-1]) / 1000
    for suffix, mul in (("Gi", 1024 ** 3), ("Mi", 1024 ** 2), ("Ki", 1024)):
        if q.endswith(suffix):
            return int(q[: -len(suffix)]) * mul
    return float(q)


def translate(pod: dict) -> dict:
    spec = pod["spec"]
    found = []
    for key in ("hostNetwork", "hostPID"):
        if spec.get(key):
            found.append(f"spec.{key} ({UNSUPPORTED[('spec', key)]})")
    for v in spec.get("volumes", []):
        if "hostPath" in v:
            found.append(f"volumes[{v['name']}].hostPath ({UNSUPPORTED[('volumes', 'hostPath')]})")
    for c in spec["containers"]:
        if c.get("securityContext", {}).get("privileged"):
            found.append(f"containers[{c['name']}].securityContext.privileged "
                         f"({UNSUPPORTED[('securityContext', 'privileged')]})")
    if found:
        raise Unsupported("; ".join(found))
    return {"app": pod["metadata"]["name"], "labels": dict(pod["metadata"].get("labels", {})),
            "units": [{"name": c["name"], "image": c["image"],
                       "cpu": quantity(c.get("resources", {}).get("requests", {}).get("cpu", "0")),
                       "memory": quantity(c.get("resources", {}).get("requests", {}).get("memory", "0"))}
                      for c in spec["containers"]]}


def project_status(state: str) -> str:
    return PHASES.get(state, "Unknown")


class KubernetesIntegrationMechanismComponent(Component):
    """Master-applied component for INV-67."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _pod(self, **extra):
        pod = {"metadata": {"name": "web", "labels": {"app": "web"}},
               "spec": {"containers": [{"name": "c", "image": "registry/web:1",
                                        "resources": {"requests": {"cpu": "250m", "memory": "512Mi"}}}]}}
        pod["spec"].update(extra)
        return pod

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        req = translate(self._pod())
        u = req["units"][0]
        assert u["cpu"] == 0.25 and u["memory"] == 512 * 1024 ** 2 and req["labels"] == {"app": "web"}
        assert project_status("exited-0") == "Succeeded" and project_status("weird") == "Unknown"
        findings[0] = self.satisfied(
            items[0],
            "A pod translates into a placement request with its requests preserved exactly (250m to 0.25 "
            "CPU, 512Mi to 536870912 bytes) and labels kept for selection; runtime state projects back "
            "as pod phases, with anything unrecognised reported Unknown rather than guessed.",
            *self._evidence("component.py::translate", "component.py::project_status"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pod = self._pod(hostNetwork=True, volumes=[{"name": "docker", "hostPath": {"path": "/var/run"}}])
        pod["spec"]["containers"][0]["securityContext"] = {"privileged": True}
        try:
            translate(pod)
            refused = ""
        except Unsupported as exc:
            refused = str(exc)
        assert refused.count(";") == 2 and "privileged" in refused and "hostPath" in refused
        findings[0] = self.satisfied(
            items[0],
            "A pod asking for host networking, a host path mount and a privileged container is refused "
            "with all three fields named, rather than being translated into something that quietly "
            "behaves differently from what was asked.",
            *self._evidence("component.py::translate", "component.py::UNSUPPORTED"))
        return findings

COMPONENT = KubernetesIntegrationMechanismComponent
