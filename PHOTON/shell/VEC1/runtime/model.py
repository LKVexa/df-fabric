from __future__ import annotations

import math
import re
from fractions import Fraction

from .canonical import canonical_json, sha256_json

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
ELECTRON_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
INTERPOLATIONS = ("linear", "step")
STATUSES = ("ACTIVE", "SUSPENDED", "RETIRED")

MAX_NAME = 128
MAX_OBJECT_ID = 128
MAX_OBJECTS = 5000
MAX_KEYFRAMES = 20000
MAX_OBSERVATIONS = 5000


def object_hash(obj):
    return sha256_json(obj)


def state_hash(state):
    body = {k: v for k, v in state.items() if k != "state_hash"}
    return sha256_json(body)


def refresh_hash(state):
    state["state_hash"] = state_hash(state)
    return state["state_hash"]


def validate_sha256(value):
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError("expected 64-hex SHA-256")
    return value.lower()


def _plain_int(value, field: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    return value


def _bounded_text(value, field: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{field} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    if any(ord(c) < 32 for c in value):
        raise ValueError(f"{field} contains control characters")
    return value


def _electron_id(value, field: str = "electron_id") -> str:
    if not isinstance(value, str) or not ELECTRON_ID.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def new_electron(electron_id: str, name: str, parent_id=None, generation=0, lineage=None):
    state = {
        "schema": "VEC1/ELECTRON_STATE/1",
        "electron_id": electron_id,
        "name": name,
        "generation": int(generation),
        "parent_id": parent_id,
        "lineage": list(lineage or []),
        "status": "ACTIVE",
        "logical_tick": 0,
        "orbital": "renderer",
        "node_preference": "AUTO",
        "objects": {},
        "animation": {"timebase": {"numerator": 1, "denominator": 60}, "keyframes": []},
        "ocr_observations": [],
        "checkpoints": [],
        "clone_counter": 0,
        "metadata": {"authoritative_state": "canonical JSON", "renderer_cache_authoritative": False},
    }
    state["state_hash"] = state_hash(state)
    return state


def validate_state(state, expected_electron_id: str | None = None, verify_hash: bool = True):
    """Validate a persisted VEC1 electron before it can participate in runtime work.

    The state hash is an integrity checksum, not an authenticity signature.  This
    validator therefore enforces the runtime's structural and semantic invariants
    even when a user or tool has recomputed the outer hash after editing JSON.
    Valid, schema-conforming user edits remain loadable.
    """
    if not isinstance(state, dict):
        raise ValueError("electron state must be a JSON object")
    canonical_json(state)  # depth, finite-number, item-count and byte-size gate

    if state.get("schema") != "VEC1/ELECTRON_STATE/1":
        raise ValueError("unsupported electron state schema")
    eid = _electron_id(state.get("electron_id"))
    if expected_electron_id is not None and eid != expected_electron_id:
        raise ValueError(f"state file identity mismatch for {expected_electron_id}")
    _bounded_text(state.get("name"), "name", MAX_NAME)

    generation = _plain_int(state.get("generation"), "generation", 0)
    parent_id = state.get("parent_id")
    if parent_id is not None:
        _electron_id(parent_id, "parent_id")
    lineage = state.get("lineage")
    if not isinstance(lineage, list):
        raise ValueError("lineage must be an array")
    for i, ancestor in enumerate(lineage):
        _electron_id(ancestor, f"lineage[{i}]")
    if eid in lineage or len(set(lineage)) != len(lineage):
        raise ValueError("lineage contains a cycle or duplicate ancestor")
    if generation != len(lineage):
        raise ValueError("generation must equal lineage depth")
    if generation == 0:
        if parent_id is not None or lineage:
            raise ValueError("generation-zero electron cannot have a parent lineage")
    elif parent_id != lineage[-1]:
        raise ValueError("parent_id must match the last lineage entry")

    if state.get("status") not in STATUSES:
        raise ValueError("invalid electron lifecycle status")
    _plain_int(state.get("logical_tick"), "logical_tick", 0)
    _bounded_text(state.get("orbital"), "orbital", MAX_OBJECT_ID)
    _bounded_text(state.get("node_preference"), "node_preference", MAX_OBJECT_ID)

    objects = state.get("objects")
    if not isinstance(objects, dict):
        raise ValueError("objects must be an object map")
    if len(objects) > MAX_OBJECTS:
        raise ValueError("object limit exceeded in persisted state")
    for oid, obj in objects.items():
        _bounded_text(oid, "object_id", MAX_OBJECT_ID)
        if not isinstance(obj, dict):
            raise ValueError(f"object {oid} must be a JSON object")
        if obj.get("object_id") != oid:
            raise ValueError(f"object {oid} identity mismatch")
        actual = validate_sha256(obj.get("object_hash"))
        body = {k: v for k, v in obj.items() if k != "object_hash"}
        if actual != object_hash(body):
            raise ValueError(f"object hash mismatch for {oid}")

    animation = state.get("animation")
    if not isinstance(animation, dict):
        raise ValueError("animation must be an object")
    timebase = animation.get("timebase")
    if not isinstance(timebase, dict):
        raise ValueError("animation.timebase must be an object")
    _plain_int(timebase.get("numerator"), "animation.timebase.numerator", 1)
    _plain_int(timebase.get("denominator"), "animation.timebase.denominator", 1)
    frames = animation.get("keyframes")
    if not isinstance(frames, list):
        raise ValueError("animation.keyframes must be an array")
    if len(frames) > MAX_KEYFRAMES:
        raise ValueError("keyframe limit exceeded in persisted state")
    seen_tracks = set()
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"keyframe[{i}] must be an object")
        _bounded_text(frame.get("id"), f"keyframe[{i}].id", MAX_OBJECT_ID)
        oid = _bounded_text(frame.get("object_id"), f"keyframe[{i}].object_id", MAX_OBJECT_ID)
        prop = _bounded_text(frame.get("property"), f"keyframe[{i}].property", MAX_OBJECT_ID)
        tick = _plain_int(frame.get("tick"), f"keyframe[{i}].tick", 0)
        interp = frame.get("interpolation", "linear")
        if interp not in INTERPOLATIONS:
            raise ValueError(f"keyframe[{i}] has invalid interpolation")
        if oid not in objects:
            raise ValueError(f"keyframe[{i}] references missing object {oid}")
        key = (oid, prop, tick)
        if key in seen_tracks:
            raise ValueError(f"duplicate keyframe at {oid}.{prop}@{tick}")
        seen_tracks.add(key)

    observations = state.get("ocr_observations")
    if not isinstance(observations, list):
        raise ValueError("ocr_observations must be an array")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValueError("observation limit exceeded in persisted state")
    seen_observations = set()
    for i, obs in enumerate(observations):
        if not isinstance(obs, dict):
            raise ValueError(f"ocr_observations[{i}] must be an object")
        oid = _bounded_text(obs.get("id"), f"ocr_observations[{i}].id", MAX_OBJECT_ID)
        if oid in seen_observations:
            raise ValueError(f"duplicate OCR observation id {oid}")
        seen_observations.add(oid)
        validate_sha256(obs.get("source_sha256"))
        if not isinstance(obs.get("raw_text"), str):
            raise ValueError(f"ocr_observations[{i}].raw_text must be a string")
        confidence = obs.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(float(confidence)):
            raise ValueError(f"ocr_observations[{i}].confidence must be finite numeric")
        if not 0 <= confidence <= 1:
            raise ValueError(f"ocr_observations[{i}].confidence must be 0..1")
        if not isinstance(obs.get("geometry"), dict):
            raise ValueError(f"ocr_observations[{i}].geometry must be an object")
        if obs.get("authoritative") is not False:
            raise ValueError("OCR observations must remain non-authoritative until explicit commit")
        _plain_int(obs.get("logical_tick"), f"ocr_observations[{i}].logical_tick", 0)

    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, list):
        raise ValueError("checkpoints must be an array")
    seen_checkpoints = set()
    for i, rec in enumerate(checkpoints):
        if not isinstance(rec, dict):
            raise ValueError(f"checkpoints[{i}] must be an object")
        cp_hash = validate_sha256(rec.get("hash"))
        if cp_hash in seen_checkpoints:
            raise ValueError(f"duplicate checkpoint {cp_hash}")
        seen_checkpoints.add(cp_hash)
        _plain_int(rec.get("tick"), f"checkpoints[{i}].tick", 0)
        expected_rel = f"checkpoints/{eid}/{cp_hash}.json"
        if rec.get("relative_path") != expected_rel:
            raise ValueError(f"checkpoint {cp_hash} has a non-canonical relative_path")

    _plain_int(state.get("clone_counter"), "clone_counter", 0)
    if not isinstance(state.get("metadata"), dict):
        raise ValueError("metadata must be an object")

    if verify_hash:
        declared = validate_sha256(state.get("state_hash"))
        expected = state_hash(state)
        if declared != expected:
            raise ValueError(f"state hash mismatch for {eid}")
    return state


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _exact(n, d, a, b):
    """Exact rational interpolation a + (b-a)*n/d. Integral results stay int so
    the canonical state hash does not depend on float formatting."""
    if isinstance(a, int) and isinstance(b, int):
        r = Fraction(a) + (Fraction(b) - Fraction(a)) * Fraction(n, d)
        return int(r) if r.denominator == 1 else float(r)
    r = Fraction(a) + (Fraction(b) - Fraction(a)) * Fraction(n, d)
    return float(r)


def animation_value(state, object_id, prop, tick):
    frames = [k for k in state["animation"]["keyframes"] if k["object_id"] == object_id and k["property"] == prop]
    frames = sorted(frames, key=lambda x: (x["tick"], x["id"]))
    if not frames:
        return None
    before = [f for f in frames if f["tick"] <= tick]
    after = [f for f in frames if f["tick"] >= tick]
    a = before[-1] if before else frames[0]
    b = after[0] if after else frames[-1]
    if a["tick"] == b["tick"]:
        return a["value"]
    if a.get("interpolation", "linear") == "step":
        return a["value"]
    if _is_number(a["value"]) and _is_number(b["value"]):
        return _exact(tick - a["tick"], b["tick"] - a["tick"], a["value"], b["value"])
    return a["value"]
