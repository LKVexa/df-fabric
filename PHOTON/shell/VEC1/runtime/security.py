from __future__ import annotations

from pathlib import Path

from .canonical import sha256_json

DEFAULT_CAPABILITIES = {
    "state.read", "state.write", "object.edit", "animation.edit",
    "ocr.observe", "ocr.commit", "clone.create", "checkpoint.create",
    "checkpoint.restore", "lifecycle.control", "fabric.verify.reference",
    "shell.shutdown",
}
METHODS_ALLOWED_WHILE_SUSPENDED = {"resume", "retire", "checkpoint", "cross_target.verify"}
METHODS_ALLOWED_WHILE_RETIRED = {"restore", "cross_target.verify"}
DENIED_BY_DEFAULT = {"network.outbound", "network.listen.public", "host.execute", "host.admin", "plugin.unsigned"}

METHOD_CAPABILITY = {
    "object.upsert": "object.edit", "object.delete": "object.edit",
    "animation.keyframe": "animation.edit", "animation.tick": "animation.edit",
    "ocr.observe": "ocr.observe", "ocr.commit": "ocr.commit",
    "clone": "clone.create", "checkpoint": "checkpoint.create", "restore": "checkpoint.restore",
    "suspend": "lifecycle.control", "resume": "lifecycle.control", "retire": "lifecycle.control",
    "cross_target.verify": "fabric.verify.reference", "fabric.diagnostic": "fabric.verify.reference",
    "shell.shutdown": "shell.shutdown",
}


class SecurityError(PermissionError):
    pass


class SecurityPolicy:
    def __init__(self, runtime_root: Path, capabilities=None):
        self.runtime_root = Path(runtime_root).resolve()
        # An explicitly empty set means deny-all.  v0.3.0 used `capabilities or
        # DEFAULT_CAPABILITIES`, accidentally converting an empty policy into the
        # default grant set.
        self.capabilities = set(DEFAULT_CAPABILITIES if capabilities is None else capabilities)

    def require(self, method: str):
        cap = METHOD_CAPABILITY.get(method)
        if cap is None:
            raise ValueError(f"unsupported operation {method}")
        if cap not in self.capabilities:
            raise SecurityError(f"capability denied: {cap}")
        return cap

    def safe_path(self, candidate) -> Path:
        p = (self.runtime_root / candidate).resolve()
        if p != self.runtime_root and self.runtime_root not in p.parents:
            raise SecurityError("path escapes VEC1 runtime sandbox")
        return p

    def capability_manifest(self):
        body = {
            "schema": "VEC1/CAPABILITY_MANIFEST/1",
            "allow": sorted(self.capabilities),
            "deny": sorted(DENIED_BY_DEFAULT),
            "filesystem_root": str(self.runtime_root),
            "network": {"listen": "127.0.0.1 only", "outbound": "not implemented/denied by VEC1 runtime"},
            "host_calls": "not implemented/denied",
            "plugins": "not implemented/denied",
        }
        return {**body, "capability_hash": sha256_json(body)}
