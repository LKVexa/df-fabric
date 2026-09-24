from __future__ import annotations
import json, threading, copy, math
from pathlib import Path
from . import VERSION
from .canonical import atomic_write_json, sha256_json, canonical_json, strict_json_loads
from .ledger import AppendOnlyLedger
from .security import SecurityPolicy, SecurityError, METHODS_ALLOWED_WHILE_SUSPENDED, METHODS_ALLOWED_WHILE_RETIRED
from .model import (
    new_electron, refresh_hash, state_hash, object_hash, validate_sha256, validate_state,
    animation_value, INTERPOLATIONS, ELECTRON_ID, MAX_NAME, MAX_OBJECT_ID,
    MAX_OBJECTS, MAX_KEYFRAMES, MAX_OBSERVATIONS,
)
from .scheduler import place
from .fabric_bridge import FabricBridge, NODE_DIRS, attestation_contract_error
from .release_integrity import verify_release

class ConflictError(RuntimeError): pass
class NotFoundError(KeyError): pass


def _text(value, field, maximum, *, allow_empty=False, strip=False):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip() if strip else value
    if not allow_empty and not text:
        raise ValueError(f"{field} must not be empty")
    if len(text) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    if any(ord(c) < 32 for c in text):
        raise ValueError(f"{field} contains control characters")
    return text

def _name(value, default):
    if value is None:
        value = default
    text = _text(value, "name", MAX_NAME, strip=True)
    return text or default

def _int(payload, key, default):
    v = payload.get(key, default)
    if isinstance(v, bool):
        raise ValueError(f"{key} must be an integer")
    if isinstance(v, float) and not v.is_integer():
        raise ValueError(f"{key} must be an integer")
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer")

def _bool(payload, key, default=False):
    v = payload.get(key, default)
    if not isinstance(v, bool):
        raise ValueError(f"{key} must be a boolean")
    return v

class VECService:
    def __init__(self, package_root: Path, fabric: FabricBridge | None = None):
        self.package_root = Path(package_root).resolve()
        self.vec_root = self.package_root / "VEC1"
        self.state_root = self.vec_root / "runtime_state"
        self.electrons_root = self.state_root / "electrons"
        self.checkpoints_root = self.state_root / "checkpoints"
        self.electrons_root.mkdir(parents=True, exist_ok=True)
        self.checkpoints_root.mkdir(parents=True, exist_ok=True)
        self.ledger = AppendOnlyLedger(self.state_root / "ledgers/events.jsonl")
        self.security = SecurityPolicy(self.state_root)
        self.fabric = fabric or FabricBridge(self.package_root)
        self._lock = threading.RLock()

    # ---- storage -------------------------------------------------------
    def _path(self, eid):
        if not isinstance(eid, str) or not ELECTRON_ID.fullmatch(eid):
            raise ValueError("invalid electron id")
        return self.security.safe_path(Path("electrons") / f"{eid}.json")

    def _checkpoint_path(self, eid, cp_hash):
        cp_hash = validate_sha256(cp_hash)  # v0.1.0 accepted "../" here (sandbox escape)
        self._path(eid)
        return self.security.safe_path(Path("checkpoints") / eid / f"{cp_hash}.json"), cp_hash

    def list_electrons(self):
        out = []
        for p in sorted(self.electrons_root.glob("*.json")):
            try:
                s = strict_json_loads(p.read_text(encoding="utf-8"))
                row = {k: s.get(k) for k in ["electron_id", "name", "generation", "parent_id", "status", "logical_tick", "orbital", "node_preference", "state_hash"]}
                if not isinstance(s, dict) or s.get("electron_id") != p.stem:
                    row["integrity"] = "IDENTITY_MISMATCH"
                elif s.get("state_hash") != state_hash(s):
                    row["integrity"] = "HASH_MISMATCH"
                else:
                    try:
                        validate_state(s, p.stem)
                        row["integrity"] = "OK"
                    except Exception as e:
                        row["integrity"] = "SCHEMA_INVALID"
                        row["detail"] = str(e)
            except Exception as e:
                row = {"electron_id": p.stem, "integrity": "UNREADABLE", "detail": type(e).__name__}
            out.append(row)
        return out

    def load(self, eid):
        p = self._path(eid)
        if not p.exists():
            raise NotFoundError(eid)
        try:
            s = strict_json_loads(p.read_text(encoding="utf-8"))
            validate_state(s, eid)
        except (ValueError, UnicodeDecodeError) as e:
            raise ConflictError(str(e)) from e
        return s

    def save(self, s):
        refresh_hash(s)
        validate_state(s, s.get("electron_id"))
        atomic_write_json(self._path(s["electron_id"]), s)
        return s

    # ---- lifecycle -----------------------------------------------------
    def create(self, name="Electron", electron_id=None, parent_id=None):
        name = _name(name, "Electron")
        with self._lock:
            if electron_id is None:
                seed = {"name": name, "existing": [e["electron_id"] for e in self.list_electrons()]}
                electron_id = "e-" + sha256_json(seed)[:16]
                i = 0
                while self._path(electron_id).exists():
                    i += 1; electron_id = "e-" + sha256_json({**seed, "i": i})[:16]
            if self._path(electron_id).exists():
                raise ConflictError("electron id already exists")
            lineage = []; generation = 0
            if parent_id:
                parent = self.load(parent_id); generation = parent["generation"] + 1; lineage = parent["lineage"] + [parent_id]
            s = new_electron(electron_id, name, parent_id, generation, lineage)
            self.save(s)
            self.ledger.append(electron_id, 0, "electron.created", {"name": name, "parent_id": parent_id, "state_hash": s["state_hash"]})
            return s

    def _precondition(self, s, expected):
        if expected is None:
            return
        expected = validate_sha256(expected)
        if s["state_hash"] != expected:
            raise ConflictError(f"state precondition failed: expected {expected}, current {s['state_hash']}")

    def _lifecycle_gate(self, s, method):
        if s["status"] == "RETIRED" and method not in METHODS_ALLOWED_WHILE_RETIRED:
            raise ConflictError("retired electron is immutable (restore a checkpoint to reactivate)")
        if s["status"] == "SUSPENDED" and method not in METHODS_ALLOWED_WHILE_SUSPENDED:
            raise ConflictError(f"electron is suspended; '{method}' requires resume first")

    def operate(self, eid, method, payload):
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
        self.security.require(method)
        canonical_json(payload)  # enforce depth/size/finite-number limits before touching state
        with self._lock:
            s = self.load(eid)
            self._precondition(s, payload.get("expected_state_hash"))
            self._lifecycle_gate(s, method)
            before = s["state_hash"]
            result = {}
            workload = "interactive_state"
            if method == "object.upsert":
                oid = _text(payload.get("object_id", ""), "object_id", MAX_OBJECT_ID, strip=True)
                obj = copy.deepcopy(payload.get("object", {}))
                if not isinstance(obj, dict): raise ValueError("object must be JSON object")
                if oid not in s["objects"] and len(s["objects"]) >= MAX_OBJECTS: raise ValueError("object limit reached")
                obj.pop("object_hash", None)
                obj = {**obj, "object_id": oid}  # v0.1.0 let the body override object_id
                obj["object_hash"] = object_hash(obj)
                s["objects"][oid] = obj; result = {"object": obj}; workload = "object_edit"
            elif method == "object.delete":
                oid = _text(payload.get("object_id", ""), "object_id", MAX_OBJECT_ID, strip=True)
                if oid not in s["objects"]: raise NotFoundError(oid)
                old = s["objects"].pop(oid)
                dropped = [k["id"] for k in s["animation"]["keyframes"] if k["object_id"] == oid]
                s["animation"]["keyframes"] = [k for k in s["animation"]["keyframes"] if k["object_id"] != oid]
                result = {"deleted": old, "dropped_keyframes": dropped}; workload = "object_edit"
            elif method == "animation.keyframe":
                oid = _text(payload.get("object_id", ""), "object_id", MAX_OBJECT_ID, strip=True)
                prop = _text(payload.get("property", ""), "property", MAX_OBJECT_ID, strip=True)
                tick = _int(payload, "tick", s["logical_tick"])
                interp = str(payload.get("interpolation", "linear"))
                if oid not in s["objects"]: raise NotFoundError(oid)
                if not prop or len(prop) > MAX_OBJECT_ID or tick < 0: raise ValueError("property and non-negative tick required")
                if interp not in INTERPOLATIONS: raise ValueError(f"interpolation must be one of {', '.join(INTERPOLATIONS)}")
                replacing = any(k["object_id"] == oid and k["property"] == prop and k["tick"] == tick for k in s["animation"]["keyframes"])
                if not replacing and len(s["animation"]["keyframes"]) >= MAX_KEYFRAMES: raise ValueError("keyframe limit reached")
                kid = "kf-" + sha256_json({"eid": eid, "oid": oid, "prop": prop, "tick": tick, "value": payload.get("value"), "interpolation": interp})[:16]
                frame = {"id": kid, "object_id": oid, "property": prop, "tick": tick, "value": payload.get("value"), "interpolation": interp}
                s["animation"]["keyframes"] = [k for k in s["animation"]["keyframes"] if not (k["object_id"] == oid and k["property"] == prop and k["tick"] == tick)]
                s["animation"]["keyframes"].append(frame)
                s["animation"]["keyframes"].sort(key=lambda k: (k["tick"], k["object_id"], k["property"], k["id"]))
                result = {"keyframe": frame}; workload = "animation_tick"
            elif method == "animation.tick":
                tick = _int(payload, "tick", s["logical_tick"] + 1)
                if tick < 0: raise ValueError("tick must be non-negative")
                s["logical_tick"] = tick
                tracks = sorted({(k["object_id"], k["property"]) for k in s["animation"]["keyframes"]})
                evaluated = {f"{o}.{p}": animation_value(s, o, p, tick) for o, p in tracks}
                result = {"tick": tick, "evaluated": evaluated}; workload = "animation_tick"
            elif method == "ocr.observe":
                src = validate_sha256(payload.get("source_sha256", ""))
                text = _text(payload.get("text", ""), "text", 262144, allow_empty=True)
                raw_confidence = payload.get("confidence", 0)
                if isinstance(raw_confidence, bool):
                    raise ValueError("confidence must be a number")
                try:
                    confidence = float(raw_confidence)
                except (TypeError, ValueError):
                    raise ValueError("confidence must be a number")
                if not math.isfinite(confidence) or not 0 <= confidence <= 1: raise ValueError("confidence must be finite and 0..1")
                geom = payload.get("geometry", {})
                if not isinstance(geom, dict): raise ValueError("geometry must be object")
                preprocessing = payload.get("preprocessing", {})
                if not isinstance(preprocessing, dict): raise ValueError("preprocessing must be object")
                engine = _text(payload.get("engine", "external-bridge"), "engine", MAX_OBJECT_ID, strip=True)
                engine_version = _text(payload.get("engine_version", "unknown"), "engine_version", MAX_OBJECT_ID, strip=True)
                reading_order = payload.get("reading_order")
                if len(s["ocr_observations"]) >= MAX_OBSERVATIONS: raise ValueError("observation limit reached")
                obs_seed = {"src": src, "text": text, "confidence": confidence, "geometry": geom, "engine": engine,
                            "engine_version": engine_version, "preprocessing": preprocessing, "reading_order": reading_order,
                            "tick": s["logical_tick"]}
                obs_id = "ocr-" + sha256_json(obs_seed)[:16]
                if any(o["id"] == obs_id for o in s["ocr_observations"]):
                    raise ConflictError(f"observation {obs_id} already recorded at this tick")
                obs = {"id": obs_id, "source_sha256": src, "raw_text": text, "confidence": confidence, "geometry": geom,
                       "engine": engine, "engine_version": engine_version, "preprocessing": preprocessing,
                       "reading_order": reading_order, "authoritative": False, "logical_tick": s["logical_tick"]}
                s["ocr_observations"].append(obs); result = {"observation": obs}; workload = "ocr_bridge"
            elif method == "ocr.commit":
                obs_id = _text(payload.get("observation_id", ""), "observation_id", MAX_OBJECT_ID, strip=True)
                oid = _text(payload.get("object_id", ""), "object_id", MAX_OBJECT_ID, strip=True)
                obs = next((o for o in s["ocr_observations"] if o["id"] == obs_id), None)
                if not obs: raise NotFoundError(obs_id)
                if oid not in s["objects"] and len(s["objects"]) >= MAX_OBJECTS: raise ValueError("object limit reached")
                obj = dict(s["objects"].get(oid, {"object_id": oid, "type": "text"}))
                obj.pop("object_hash", None)
                obj["text"] = obs["raw_text"]; obj["ocr_source_observation"] = obs_id; obj["ocr_source_sha256"] = obs["source_sha256"]
                obj["object_hash"] = object_hash(obj)
                s["objects"][oid] = obj; result = {"object": obj, "committed_from": obs_id}; workload = "ocr_bridge"
            elif method == "checkpoint":
                snap = copy.deepcopy(s)
                cp_hash = sha256_json(snap)
                cp_path, _ = self._checkpoint_path(eid, cp_hash)
                cp_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_json(cp_path, snap)
                rec = {"hash": cp_hash, "tick": s["logical_tick"], "relative_path": str(cp_path.relative_to(self.state_root)).replace("\\", "/")}
                if rec not in s["checkpoints"]: s["checkpoints"].append(rec)
                result = {"checkpoint": rec}; workload = "checkpoint"
            elif method == "restore":
                cp_path, cp_hash = self._checkpoint_path(eid, payload.get("checkpoint_hash", ""))
                if not cp_path.exists(): raise NotFoundError(cp_hash)
                try:
                    restored = strict_json_loads(cp_path.read_text(encoding="utf-8"))
                except (ValueError, UnicodeDecodeError) as e:
                    raise ConflictError(f"checkpoint JSON invalid: {e}") from e
                if not isinstance(restored, dict) or sha256_json(restored) != cp_hash:
                    raise ConflictError("checkpoint content does not match its hash")
                try:
                    validate_state(restored, eid)
                except ValueError as e:
                    raise ConflictError(f"checkpoint state invalid: {e}") from e
                known = list(s["checkpoints"])  # keep checkpoints taken after the restored snapshot
                restored["checkpoints"] = known + [c for c in restored.get("checkpoints", []) if c not in known]
                restored["clone_counter"] = max(int(restored.get("clone_counter", 0)), int(s.get("clone_counter", 0)))
                restored["status"] = "ACTIVE"
                s = restored
                result = {"restored": cp_hash}; workload = "checkpoint"
            elif method in ("suspend", "resume", "retire"):
                mapping = {"suspend": "SUSPENDED", "resume": "ACTIVE", "retire": "RETIRED"}
                if method == "resume" and s["status"] != "SUSPENDED":
                    raise ConflictError("only a suspended electron can be resumed")
                if method == "suspend" and s["status"] != "ACTIVE":
                    raise ConflictError("only an active electron can be suspended")
                s["status"] = mapping[method]; result = {"status": s["status"]}; workload = "interactive_state"
            elif method == "cross_target.verify":
                require_all = _bool(payload, "require_all", False)
                verification = self.fabric.cross_target_verify({"electron_id": eid, "state_hash": s["state_hash"], "tick": s["logical_tick"]}, require_all)
                self.ledger.append(eid, s["logical_tick"], "cross_target.verify", verification)
                return {"electron": s, "result": verification, "placement": {"selected": "FABRIC", "degraded": not verification["all_four_bound"]}}
            else:
                raise ValueError(f"unsupported operation {method}")
            refresh_hash(s)
            canonical_json(s)  # size gate before persisting
            self.save(s)
            placement = place(workload, self.fabric.bound_nodes())
            self.ledger.append(eid, s["logical_tick"], method, {"before_state_hash": before, "after_state_hash": s["state_hash"], "result_hash": sha256_json(result), "placement": placement})
            return {"electron": s, "result": result, "placement": placement}

    def clone(self, eid, name=None):
        self.security.require("clone")
        with self._lock:
            p = self.load(eid)
            if p["status"] == "RETIRED":
                raise ConflictError("retired electron cannot be cloned")
            name = _name(name, p["name"] + " clone")
            parent_before = p["state_hash"]
            counter = int(p.get("clone_counter", 0)) + 1
            # Compute the deterministic clone id from the would-be parent state
            # before committing the parent counter.  A caller can create explicit
            # electron ids, so a pre-existing deterministic clone id must be a
            # conflict rather than an overwrite target.
            proposed_parent = copy.deepcopy(p)
            proposed_parent["clone_counter"] = counter
            refresh_hash(proposed_parent)
            clone_id = "e-" + sha256_json({"parent": eid, "state_hash": proposed_parent["state_hash"], "counter": counter})[:16]
            if self._path(clone_id).exists():
                raise ConflictError(f"deterministic clone id already exists: {clone_id}")
            p["clone_counter"] = counter
            self.save(p)
            c = copy.deepcopy(p)
            c["electron_id"] = clone_id; c["name"] = name
            c["parent_id"] = eid; c["generation"] = p["generation"] + 1; c["lineage"] = p["lineage"] + [eid]
            c["clone_counter"] = 0; c["checkpoints"] = []; c["status"] = "ACTIVE"
            self.save(c)
            self.ledger.append(eid, p["logical_tick"], "clone.created", {"clone_id": clone_id, "before_parent_state_hash": parent_before, "parent_state_hash": p["state_hash"], "clone_state_hash": c["state_hash"]})
            self.ledger.append(clone_id, c["logical_tick"], "electron.created_from_clone", {"parent_id": eid, "state_hash": c["state_hash"]})
            return c

    # ---- introspection --------------------------------------------------
    def verify_checkpoints(self):
        """Verify every checkpoint referenced by valid current electron state.

        Orphan files are reported for recovery/cleanup but do not fail integrity:
        a crash can legitimately leave a fully written checkpoint before the
        referencing state update is committed. Missing or corrupt *referenced*
        checkpoints fail the gate.
        """
        errors = []
        referenced = set()
        checked = 0
        for state_path in sorted(self.electrons_root.glob("*.json")):
            eid = state_path.stem
            try:
                state = self.load(eid)
            except Exception:
                continue  # electron integrity is reported by the separate gate
            for rec in state.get("checkpoints", []):
                cp_hash = rec["hash"]
                try:
                    cp_path, _ = self._checkpoint_path(eid, cp_hash)
                    referenced.add(cp_path.resolve())
                    if not cp_path.is_file():
                        errors.append({"electron_id": eid, "checkpoint": cp_hash, "error": "missing referenced checkpoint"})
                        continue
                    checkpoint = strict_json_loads(cp_path.read_text(encoding="utf-8"))
                    if sha256_json(checkpoint) != cp_hash:
                        errors.append({"electron_id": eid, "checkpoint": cp_hash, "error": "checkpoint content hash mismatch"})
                        continue
                    validate_state(checkpoint, eid)
                    if rec.get("tick") != checkpoint.get("logical_tick"):
                        errors.append({
                            "electron_id": eid, "checkpoint": cp_hash,
                            "error": f"checkpoint metadata tick {rec.get('tick')} does not match snapshot tick {checkpoint.get('logical_tick')}",
                        })
                        continue
                    checked += 1
                except Exception as e:
                    errors.append({"electron_id": eid, "checkpoint": cp_hash, "error": f"{type(e).__name__}: {e}"})
        actual = {p.resolve() for p in self.checkpoints_root.rglob("*.json") if p.is_file()}
        orphans = sorted(str(p.relative_to(self.state_root)).replace("\\", "/") for p in actual - referenced)
        return {
            "ok": not errors,
            "checked": checked,
            "referenced": len(referenced),
            "errors": errors[:100],
            "error_count": len(errors),
            "orphans": orphans[:100],
            "orphan_count": len(orphans),
        }

    def fabric_diagnostic(self):
        self.security.require("fabric.diagnostic")
        return self.fabric.run_fabric_diagnostic()

    def verify_all(self, include_release=False):
        """Full integrity sweep used by --verify-only; never raises."""
        report = {"schema": "VEC1/VERIFY/1", "version": VERSION, "ok": True, "checks": {}}
        try:
            report["checks"]["ledger"] = self.ledger.verify()
        except Exception as e:
            report["ok"] = False; report["checks"]["ledger"] = {"ok": False, "error": str(e)}
        electrons = self.list_electrons()
        bad = [e for e in electrons if e.get("integrity") != "OK"]
        report["checks"]["electrons"] = {"ok": not bad, "count": len(electrons), "failing": bad}
        if bad: report["ok"] = False
        checkpoints = self.verify_checkpoints()
        report["checks"]["checkpoints"] = checkpoints
        if not checkpoints.get("ok"): report["ok"] = False
        try:
            att = self.fabric.attest(fresh=True)
            rc = att.get("_returncode")
            nodes = att.get("nodes", {}) if isinstance(att.get("nodes"), dict) else {}
            contract_error = attestation_contract_error(att)
            att_error = att.get("error") or att.get("parse_error") or contract_error
            required_records = isinstance(nodes, dict) and set(NODE_DIRS).issubset(nodes)
            bad_sums = sorted(
                n for n in NODE_DIRS
                if isinstance(nodes.get(n), dict)
                and nodes[n].get("present") is True
                and nodes[n].get("sums_match") is not True
            )
            fabric_ok = rc == 0 and not att_error and required_records and not bad_sums
            report["checks"]["fabric"] = {
                "ok": fabric_ok,
                "returncode": rc,
                "bound_nodes": self.bound_nodes_from(att),
                "required_node_records": required_records,
                "checksum_failures": bad_sums,
                **({"error": str(att_error)} if att_error else {}),
            }
            if not fabric_ok: report["ok"] = False
        except Exception as e:
            report["ok"] = False
            report["checks"]["fabric"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        if include_release:
            try:
                rel = verify_release(self.package_root)
            except Exception as e:
                rel = {"schema": "VEC1/RELEASE_VERIFY/1", "ok": False, "errors": [f"{type(e).__name__}: {e}"]}
            report["checks"]["release"] = rel
            if not rel.get("ok"): report["ok"] = False
        return report

    @staticmethod
    def bound_nodes_from(att):
        nodes = att.get("nodes", {}) if isinstance(att.get("nodes"), dict) else {}
        return sorted(
            n for n in NODE_DIRS
            if isinstance(nodes.get(n), dict)
            and nodes[n].get("present") is True
            and nodes[n].get("bound") is True
            and nodes[n].get("sums_match") is True
        )

    def status(self):
        att = self.fabric.attest()
        nodes = att.get("nodes", {}) if isinstance(att.get("nodes"), dict) else {}
        fabric_error = att.get("error") or att.get("parse_error") or attestation_contract_error(att)
        try:
            ledger = self.ledger.health()
        except Exception as e:
            ledger = {"ok": False, "error": str(e), "events": 0}
        return {
            "schema": "VEC1/STATUS/1",
            "version": VERSION,
            "renderer": "system Edge/Chrome/Chromium app mode (isolated profile) when available; default browser fallback",
            "network_boundary": "HTTP server binds 127.0.0.1 only, enforces Host/Origin allowlist and a per-launch session token; VEC runtime implements no outbound network client",
            "electrons": self.list_electrons(),
            "fabric_nodes": {k: {"present": v.get("present"), "bound": v.get("bound"), "sums_match": v.get("sums_match")} for k, v in nodes.items() if isinstance(v, dict)},
            "fabric_error": fabric_error,
            "capabilities": self.security.capability_manifest(),
            "ledger": ledger,
            "claim_boundary": "Functional local reference shell and deterministic VEC state/bridge. Not a drop-in Electron API implementation; full VEC semantics are not lowered into every VM ISA.",
        }
