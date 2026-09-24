import json, tempfile, unittest, sys, hashlib
from pathlib import Path
HERE=Path(__file__).resolve()
VEC=HERE.parents[1]
ROOT=VEC.parent
sys.path.insert(0,str(VEC))
from runtime.canonical import sha256_json
from runtime.ledger import AppendOnlyLedger, LedgerIntegrityError
from runtime.model import new_electron, refresh_hash, animation_value
from runtime.scheduler import place
from runtime.vm_lowering import witness_for, lower_small, lower_medium, lower_large, lower_xlarge
from runtime.security import SecurityPolicy, SecurityError
from runtime.fabric_bridge import FabricBridge, NODE_DIRS, FABRIC_AGREE, REPLAY_PASS
from runtime.instance_lock import SingleInstanceLock, InstanceLockError

class Tests(unittest.TestCase):
    def test_canonical_hash_order(self):
        self.assertEqual(sha256_json({"b":2,"a":1}),sha256_json({"a":1,"b":2}))
    def test_ledger_chain(self):
        with tempfile.TemporaryDirectory() as td:
            l=AppendOnlyLedger(Path(td)/"x.jsonl")
            l.append("e",0,"a",{"x":1}); l.append("e",1,"b",{"x":2})
            self.assertTrue(l.verify()["ok"])
    def test_animation_interpolation(self):
        s=new_electron("e","x")
        s["objects"]["o"]={"object_id":"o"}
        s["animation"]["keyframes"]=[
            {"id":"a","object_id":"o","property":"x","tick":0,"value":0},
            {"id":"b","object_id":"o","property":"x","tick":10,"value":100}]
        self.assertEqual(animation_value(s,"o","x",5),50)
    def test_scheduler(self):
        p=place("device_io",["N_SMALL","N_LARGE"])
        self.assertEqual(p["selected"],"N_LARGE")
    def test_lowerers_embed_same_witness(self):
        w=witness_for({"x":1})
        for fn in [lower_small,lower_medium,lower_large,lower_xlarge]:
            self.assertIn(str(w),fn(w))
    def test_witness_is_actual_digest_low64(self):
        payload = {"x": 1}
        expected = int(sha256_json(payload)[-16:], 16)
        w = witness_for(payload)
        self.assertEqual(w, expected)
        self.assertLess(w, 1 << 64)

    def test_explicit_empty_capability_set_is_deny_all(self):
        with tempfile.TemporaryDirectory() as td:
            s = SecurityPolicy(Path(td), capabilities=set())
            with self.assertRaises(SecurityError): s.require("object.upsert")
            self.assertEqual(s.capability_manifest()["allow"], [])
            self.assertEqual(len(s.capability_manifest()["capability_hash"]), 64)

    def test_cross_target_require_all_ignores_unknown_bound_node(self):
        with tempfile.TemporaryDirectory() as td:
            b = FabricBridge(Path(td))
            nodes = {n: {"present": n != "N_XLARGE", "bound": n != "N_XLARGE", "sums_match": True if n != "N_XLARGE" else None} for n in NODE_DIRS}
            nodes["N_BOGUS"] = {"present": True, "bound": True, "sums_match": True}
            b.attest = lambda fresh=False: {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 0, "nodes": nodes}
            b._run_json = lambda *a, **k: {"_returncode": 0, "result": {"result_low64": 0}}
            r = b.cross_target_verify({"x": 1}, require_all=True)
            self.assertEqual(r["status"], "BLOCKED")
            self.assertFalse(r["all_four_bound"]); self.assertIn("N_BOGUS", r["unknown_bound_nodes_ignored"])

    def test_cross_target_fails_closed_on_attestation_error(self):
        with tempfile.TemporaryDirectory() as td:
            b = FabricBridge(Path(td))
            b.attest = lambda fresh=False: {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 2, "error": "synthetic", "nodes": {n: {"present": True, "bound": True, "sums_match": True} for n in NODE_DIRS}}
            r = b.cross_target_verify({"x": 1})
            self.assertEqual(r["status"], "BLOCKED"); self.assertIn("synthetic", r["attestation_error"])
            self.assertTrue(all(v["status"] == "NOT_RUN" for v in r["results"].values()))

    def test_diagnostic_nonzero_returncode_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); fabric = root / "DF_Fabric"; (fabric / "adapter/dfabric").mkdir(parents=True); (fabric / "examples").mkdir()
            (fabric / "adapter/dfabric/cli.py").write_text("# fixture")
            (fabric / "examples/01_bell_pair.pal").write_text("fixture")
            b = FabricBridge(root)
            b._run_json = lambda *a, **k: {"_returncode": 2, "verdict": "PASS"}
            r = b.run_fabric_diagnostic()
            self.assertEqual(r["verdict"], "FAIL"); self.assertEqual(r["adapter_verdict"], "PASS")

    def test_cross_target_routes_adapter_output_outside_sealed_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            b = FabricBridge(root)
            nodes = {n: {"present": n == "N_SMALL", "bound": n == "N_SMALL", "sums_match": True if n == "N_SMALL" else None} for n in NODE_DIRS}
            b.attest = lambda fresh=False: {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 0, "nodes": nodes}
            seen = []
            def fake_run(cwd, argv, timeout=60):
                seen.append(list(argv))
                witness = witness_for({"x": 1})
                return {"_returncode": 0, "result": {"result_low64": witness}}
            b._run_json = fake_run
            r = b.cross_target_verify({"x": 1})
            self.assertEqual(r["status"], "PASS")
            node_calls = [a for a in seen if "node-run" in a]
            self.assertEqual(len(node_calls), 1)
            self.assertIn("--out", node_calls[0])
            out_path = Path(node_calls[0][node_calls[0].index("--out") + 1])
            self.assertNotIn(str(root / "DF_Small"), str(out_path))

    def test_diagnostic_requires_known_agreement_and_replay_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); fabric = root / "DF_Fabric"; (fabric / "adapter/dfabric").mkdir(parents=True); (fabric / "examples").mkdir()
            (fabric / "adapter/dfabric/cli.py").write_text("# fixture")
            (fabric / "examples/01_bell_pair.pal").write_text("fixture")
            b = FabricBridge(root)
            calls = []
            b._run_json = lambda cwd, argv, timeout=60: (calls.append(list(argv)) or {"_returncode": 0, "verdict": "BANANA", "event_log": {"replay_self_check": {"token": REPLAY_PASS}}, "programs": {}})
            r = b.run_fabric_diagnostic()
            self.assertEqual(r["verdict"], "FAIL")
            self.assertIn("did not report", r["error"])
            self.assertIn("--out", calls[0])

    def test_single_instance_lock_refuses_second_owner(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".vec1.lock"
            a, b = SingleInstanceLock(path), SingleInstanceLock(path)
            a.acquire()
            try:
                with self.assertRaises(InstanceLockError):
                    b.acquire()
            finally:
                a.release()
            b.acquire(); b.release()

    def test_sandbox(self):
        with tempfile.TemporaryDirectory() as td:
            s=SecurityPolicy(Path(td))
            with self.assertRaises(SecurityError): s.safe_path("../escape")

if __name__=="__main__": unittest.main(verbosity=2)
