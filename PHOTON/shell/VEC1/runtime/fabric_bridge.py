from __future__ import annotations
import json, os, subprocess, tempfile, sys, threading, time
from pathlib import Path
from .vm_lowering import witness_for, LOWERERS
from .canonical import sha256_json, strict_json_loads

NODE_DIRS = {"N_SMALL": "DF_Small", "N_MEDIUM": "DF_Medium", "N_LARGE": "DF_Large", "N_XLARGE": "DF_Xtra_Large"}
ATTEST_TTL_SECONDS = 5.0
EXPECTED_ATTEST_SCHEMA = "DF/FABRIC_ATTEST/1"
FABRIC_AGREE = "CROSS_NODE_DIFFERENTIAL_AGREEMENT"
REPLAY_PASS = "DETERMINISTIC_REPLAY_PASS"


def attestation_contract_error(data):
    if not isinstance(data, dict):
        return "fabric attestation is not a JSON object"
    if data.get("schema") != EXPECTED_ATTEST_SCHEMA:
        return f"fabric attestation schema must be {EXPECTED_ATTEST_SCHEMA}"
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        return "fabric attestation did not return a nodes object"
    missing = sorted(set(NODE_DIRS) - set(nodes))
    if missing:
        return f"fabric attestation missing required node records: {', '.join(missing)}"
    for node in NODE_DIRS:
        rec = nodes.get(node)
        if not isinstance(rec, dict):
            return f"fabric attestation node {node} is not an object"
        present, bound, sums = rec.get("present"), rec.get("bound"), rec.get("sums_match")
        if not isinstance(present, bool) or not isinstance(bound, bool):
            return f"fabric attestation node {node} present/bound flags must be booleans"
        if bound and not present:
            return f"fabric attestation node {node} cannot be bound while absent"
        if present and sums is not True:
            return f"fabric attestation node {node} is present without a passing sealed checksum"
        if not present and sums is not None:
            return f"fabric attestation node {node} absent checksum state must be null"
    return None


class FabricBridge:
    def __init__(self, package_root: Path, attest_ttl: float = ATTEST_TTL_SECONDS):
        self.package_root = Path(package_root).resolve()
        self.fabric_root = self.package_root / "DF_Fabric"
        self.attest_ttl = float(attest_ttl)
        self._attest_cache = None  # (monotonic, data)
        self._lock = threading.Lock()

    def _python(self):
        return sys.executable or "python"

    def _run_json(self, cwd, argv, timeout=60):
        # -B applies only to this interpreter. Some supplied adapters spawn child
        # Python interpreters, so also propagate the environment-level no-pyc
        # policy to keep execution from mutating sealed/checksummed DF trees.
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            cp = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "_returncode": None, "error": f"timed out after {timeout}s", "argv0": Path(argv[-1]).name}
        except OSError as e:
            return {"ok": False, "_returncode": None, "error": f"could not start adapter: {e}"}
        if cp.returncode not in (0, 1, 2, 3):
            return {"ok": False, "_returncode": cp.returncode, "error": "adapter failed", "stderr_tail": cp.stderr[-1000:]}
        text = cp.stdout.strip()
        if not text:
            return {"ok": False, "_returncode": cp.returncode, "stderr_tail": cp.stderr[-2000:]}
        try:
            data = strict_json_loads(text)
        except Exception as e:
            return {"ok": False, "_returncode": cp.returncode, "parse_error": str(e), "stdout_tail": text[-4000:], "stderr_tail": cp.stderr[-2000:]}
        if not isinstance(data, dict):
            return {"ok": False, "_returncode": cp.returncode, "error": "adapter output is not a JSON object"}
        data["_returncode"] = cp.returncode
        return data

    def attest(self, fresh=False):
        """Return a validated DF_Fabric attestation, cached for a few seconds."""
        with self._lock:
            now = time.monotonic()
            if not fresh and self._attest_cache and now - self._attest_cache[0] < self.attest_ttl:
                return self._attest_cache[1]
            cli = self.fabric_root / "adapter/dfabric/cli.py"
            if not cli.exists():
                data = {"schema": "VEC1/FABRIC_ATTEST_WRAPPER/1", "error": "DF_Fabric adapter missing", "nodes": {}}
            else:
                data = self._run_json(self.fabric_root, [self._python(), "-B", str(cli), "fabric-attest"], timeout=30)
                rc = data.get("_returncode")
                if rc not in (None, 0) and not data.get("error"):
                    data["error"] = f"fabric attestation exited {rc}"
                contract_error = attestation_contract_error(data)
                if contract_error and not data.get("error") and not data.get("parse_error"):
                    data["error"] = contract_error
                if not isinstance(data.get("nodes"), dict):
                    data["nodes"] = {}
            self._attest_cache = (now, data)
            return data

    def bound_nodes(self, fresh=False):
        data = self.attest(fresh)
        if data.get("error") or data.get("parse_error"):
            return []
        nodes = data.get("nodes", {})
        return sorted(
            n for n in NODE_DIRS
            if isinstance(nodes.get(n), dict)
            and nodes[n].get("present") is True
            and nodes[n].get("bound") is True
            and nodes[n].get("sums_match") is True
        )

    def topology(self):
        p = self.fabric_root / "fabric/TOPOLOGY.json"
        if not p.exists():
            return {"schema": "VEC1/TOPOLOGY_WRAPPER/1", "error": "DF_Fabric topology missing"}
        try:
            data = strict_json_loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
            return {"schema": "VEC1/TOPOLOGY_WRAPPER/1", "error": f"DF_Fabric topology unreadable: {type(exc).__name__}"}
        if not isinstance(data, dict):
            return {"schema": "VEC1/TOPOLOGY_WRAPPER/1", "error": "DF_Fabric topology is not a JSON object"}
        return data

    def cross_target_verify(self, payload, require_all=False):
        witness = witness_for(payload)
        att = self.attest(fresh=True)
        reported_nodes = att.get("nodes", {}) if isinstance(att.get("nodes"), dict) else {}
        unknown_bound = sorted(
            n for n, v in reported_nodes.items()
            if n not in NODE_DIRS and isinstance(v, dict) and v.get("present") is True and v.get("bound") is True
        )
        bound = sorted(
            n for n in NODE_DIRS
            if isinstance(reported_nodes.get(n), dict)
            and reported_nodes[n].get("present") is True
            and reported_nodes[n].get("bound") is True
            and reported_nodes[n].get("sums_match") is True
        )
        attestation_error = att.get("error") or att.get("parse_error") or attestation_contract_error(att)
        if att.get("_returncode") not in (None, 0) and not attestation_error:
            attestation_error = f"fabric attestation exited {att.get('_returncode')}"
        if attestation_error:
            return {
                "schema": "VEC1/CROSS_TARGET_VERIFICATION/1",
                "status": "BLOCKED",
                "require_all": bool(require_all),
                "payload_sha256": sha256_json(payload),
                "witness_low64": witness,
                "bound_nodes": [],
                "unknown_bound_nodes_ignored": unknown_bound,
                "all_four_bound": False,
                "results": {node: {"status": "NOT_RUN", "reason": "fabric attestation failed"} for node in NODE_DIRS},
                "attestation_error": str(attestation_error),
                "normalization": "target-specific result register -> result_low64",
                "claim": "Verification is fail-closed when Fabric attestation is unavailable or invalid.",
            }
        results = {}
        with tempfile.TemporaryDirectory(prefix="vec1-witness-") as td:
            td = Path(td)
            for node in NODE_DIRS:
                if node not in bound:
                    results[node] = {"status": "NOT_RUN", "reason": "node is not currently bound/built"}
                    continue
                ext, lowerer = LOWERERS[node]
                src = td / f"{node.lower()}.{ext}"
                out_record = td / f"{node.lower()}.run.json"
                src.write_text(lowerer(witness), encoding="utf-8", newline="\n")
                nroot = self.package_root / NODE_DIRS[node]
                cli = nroot / "adapter/dfabric/cli.py"
                data = self._run_json(
                    nroot,
                    [self._python(), "-B", str(cli), "node-run", str(src), "--out", str(out_record)],
                    timeout=45,
                )
                r = data.get("result") if isinstance(data.get("result"), dict) else {}
                value = r.get("result_low64")
                results[node] = {
                    "status": "PASS" if value == witness and data.get("_returncode") == 0 else "FAIL",
                    "normalized_result_low64": value,
                    "expected_low64": witness,
                    "result_register": r.get("result_register"),
                    "guest_dialect": r.get("guest_dialect"),
                    "image_sha256": r.get("image_sha256"),
                    "signed_image_sha256": r.get("signed_image_sha256"),
                    "source_sha256": r.get("source_sha256"),
                    "node_returncode": data.get("_returncode"),
                    **({"adapter_error": data["error"]} if data.get("error") else {}),
                    **({"adapter_error": data["parse_error"]} if data.get("parse_error") else {}),
                }
        ran = [v for v in results.values() if v["status"] != "NOT_RUN"]
        passed = [v for v in ran if v["status"] == "PASS"]
        all_bound = set(bound) == set(NODE_DIRS)
        if require_all and not all_bound:
            status = "BLOCKED"
        elif not ran:
            status = "NOT_RUN"
        elif len(passed) == len(ran):
            status = "PASS"
        else:
            status = "FAIL"
        return {
            "schema": "VEC1/CROSS_TARGET_VERIFICATION/1",
            "status": status,
            "require_all": bool(require_all),
            "payload_sha256": sha256_json(payload),
            "witness_low64": witness,
            "bound_nodes": bound,
            "unknown_bound_nodes_ignored": unknown_bound,
            "all_four_bound": all_bound,
            "results": results,
            "normalization": "target-specific result register -> result_low64",
            "claim": "Verifies a deterministic canonical payload witness across the available VM adapters. It does not claim full semantic lowering of VEC object/animation/OCR operations into every VM ISA.",
        }

    def run_fabric_diagnostic(self):
        cli = self.fabric_root / "adapter/dfabric/cli.py"
        bundle = self.fabric_root / "examples/01_bell_pair.pal"
        if not cli.exists() or not bundle.exists():
            return {"schema": "VEC1/FABRIC_DIAGNOSTIC/1", "returncode": None, "verdict": "BLOCKED", "error": "DF_Fabric adapter or example missing"}
        with tempfile.TemporaryDirectory(prefix="vec1-fabric-diagnostic-") as td:
            out_record = Path(td) / "fabric-run.json"
            data = self._run_json(
                self.fabric_root,
                [self._python(), "-B", str(cli), "fabric-run", str(bundle), "--profile", "single_process_deterministic", "--placement", "static", "--out", str(out_record)],
                timeout=90,
            )
        ev = data.get("event_log") if isinstance(data.get("event_log"), dict) else {}
        progs = data.get("programs") if isinstance(data.get("programs"), dict) else {}
        replica = progs.get("replica") if isinstance(progs.get("replica"), dict) else {}
        rc = data.get("_returncode")
        adapter_error = data.get("error") or data.get("parse_error")
        raw_verdict = data.get("verdict")
        replay = (ev.get("replay_self_check") or {}).get("token") if isinstance(ev.get("replay_self_check"), dict) else None
        passed = rc == 0 and not adapter_error and raw_verdict == FABRIC_AGREE and replay == REPLAY_PASS
        verdict = "PASS" if passed else "FAIL"
        out = {
            "schema": "VEC1/FABRIC_DIAGNOSTIC/1",
            "returncode": rc,
            "verdict": verdict,
            "adapter_verdict": raw_verdict,
            "nodes_bound": data.get("nodes_bound", []),
            "nodes_absent": data.get("nodes_absent", []),
            "event_log_hash": ev.get("hash"),
            "replay": replay,
            "replica_participants": replica.get("participants"),
            "replica_unanimous": replica.get("unanimous"),
        }
        if adapter_error:
            out["error"] = str(adapter_error)
        elif rc not in (None, 0):
            out["error"] = f"fabric diagnostic exited {rc}"
        elif raw_verdict != FABRIC_AGREE:
            out["error"] = f"fabric diagnostic did not report {FABRIC_AGREE}"
        elif replay != REPLAY_PASS:
            out["error"] = f"fabric diagnostic replay did not report {REPLAY_PASS}"
        return out
