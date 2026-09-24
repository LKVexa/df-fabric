import http.client, json, shutil, tempfile, threading, unittest, sys
from pathlib import Path
HERE = Path(__file__).resolve()
VEC = HERE.parents[1]
sys.path.insert(0, str(VEC))
from runtime.service import VECService, ConflictError, NotFoundError
import runtime.service as service_module
from runtime.ledger import AppendOnlyLedger, LedgerIntegrityError
from runtime.model import new_electron, animation_value, refresh_hash
from runtime.canonical import sha256_json
from runtime.security import SecurityPolicy, SecurityError
import app as vec_app

class FakeFabric:
    """No subprocesses: service tests stay hermetic and fast."""
    def __init__(self, bound=("N_SMALL",)): self._bound = list(bound)
    def attest(self, fresh=False):
        names = ("N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE")
        return {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 0, "nodes": {n: {"present": n in self._bound, "bound": n in self._bound, "sums_match": True if n in self._bound else None} for n in names}}
    def bound_nodes(self, fresh=False): return sorted(self._bound)
    def topology(self): return {"nodes": self._bound}
    def run_fabric_diagnostic(self): return {"verdict": "FAKE"}
    def cross_target_verify(self, payload, require_all=False):
        return {"status": "NOT_RUN", "all_four_bound": False, "payload_sha256": sha256_json(payload)}

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        (self.td / "VEC1").mkdir()
        self.svc = VECService(self.td, fabric=FakeFabric())
        self.e = self.svc.create("t")["electron_id"]
    def tearDown(self): shutil.rmtree(self.td, ignore_errors=True)
    def op(self, m, **p): return self.svc.operate(self.e, m, p)

    def test_restore_rejects_path_traversal(self):
        self.op("checkpoint")
        secret = self.svc.state_root / "secret"; secret.mkdir()
        (secret / "leak.json").write_text('{"electron_id":"x"}')
        with self.assertRaises(ValueError):
            self.op("restore", checkpoint_hash="../../secret/leak")

    def test_restore_rejects_tampered_checkpoint(self):
        cp = self.op("checkpoint")["result"]["checkpoint"]
        path = self.svc.state_root / cp["relative_path"]
        data = json.loads(path.read_text()); data["name"] = "evil"; path.write_text(json.dumps(data))
        with self.assertRaises(ConflictError):
            self.op("restore", checkpoint_hash=cp["hash"])

    def test_restore_keeps_later_checkpoints(self):
        first = self.op("checkpoint")["result"]["checkpoint"]
        self.op("object.upsert", object_id="a", object={"v": 1})
        second = self.op("checkpoint")["result"]["checkpoint"]
        s = self.op("restore", checkpoint_hash=first["hash"])["electron"]
        self.assertNotIn("a", s["objects"])
        self.assertIn(second, s["checkpoints"])

    def test_object_id_cannot_be_overridden(self):
        s = self.op("object.upsert", object_id="a", object={"object_id": "b"})["electron"]
        self.assertEqual(s["objects"]["a"]["object_id"], "a")

    def test_suspended_blocks_mutation_until_resume(self):
        self.op("suspend")
        with self.assertRaises(ConflictError): self.op("object.upsert", object_id="z", object={})
        self.op("resume")
        self.op("object.upsert", object_id="z", object={})

    def test_retired_is_immutable_and_uncloneable(self):
        cp = self.op("checkpoint")["result"]["checkpoint"]
        self.op("retire")
        with self.assertRaises(ConflictError): self.op("object.upsert", object_id="z", object={})
        with self.assertRaises(ConflictError): self.svc.clone(self.e)
        self.assertEqual(self.op("restore", checkpoint_hash=cp["hash"])["electron"]["status"], "ACTIVE")

    def test_unknown_method_is_bad_request(self):
        with self.assertRaises(ValueError): self.op("host.execute")

    def test_precondition_conflict(self):
        with self.assertRaises(ConflictError): self.op("suspend", expected_state_hash="0" * 64)

    def test_delete_object_drops_keyframes(self):
        self.op("object.upsert", object_id="o", object={})
        self.op("animation.keyframe", object_id="o", property="x", tick=1, value=1)
        s = self.op("object.delete", object_id="o")["electron"]
        self.assertEqual(s["animation"]["keyframes"], [])

    def test_bad_ids_and_names(self):
        with self.assertRaises(ValueError): self.svc.load("../x")
        with self.assertRaises(ValueError): self.svc.load("a" * 65)
        with self.assertRaises(ValueError): self.svc.create("x" * 200)

    def test_name_and_object_identifiers_require_strings(self):
        with self.assertRaises(ValueError): self.svc.create({"not": "a string"})
        with self.assertRaises(ValueError): self.op("object.upsert", object_id=123, object={})

    def test_ocr_text_and_engine_require_strings(self):
        with self.assertRaises(ValueError):
            self.op("ocr.observe", source_sha256="0" * 64, text={"x": 1}, confidence=1, geometry={})
        with self.assertRaises(ValueError):
            self.op("ocr.observe", source_sha256="0" * 64, text="x", confidence=1, geometry={}, engine=7)

    def test_nonfinite_payload_rejected(self):
        with self.assertRaises(ValueError): self.op("object.upsert", object_id="a", object={"v": float("inf")})

    def test_clone_lineage_and_ledger(self):
        c = self.svc.clone(self.e)
        self.assertEqual(c["lineage"], [self.e]); self.assertEqual(c["generation"], 1)
        self.assertTrue(self.svc.ledger.verify()["ok"])
        self.assertTrue(self.svc.verify_all()["ok"])

    def test_verify_all_detects_state_tamper(self):
        p = self.svc.electrons_root / f"{self.e}.json"
        d = json.loads(p.read_text()); d["name"] = "tampered"; p.write_text(json.dumps(d))
        self.assertFalse(self.svc.verify_all()["ok"])

    def test_require_all_must_be_boolean(self):
        with self.assertRaises(ValueError):
            self.op("cross_target.verify", require_all="false")

    def test_keyframe_replacement_allowed_at_limit(self):
        self.op("object.upsert", object_id="o", object={})
        old = service_module.MAX_KEYFRAMES
        service_module.MAX_KEYFRAMES = 1
        try:
            self.op("animation.keyframe", object_id="o", property="x", tick=1, value=1)
            r = self.op("animation.keyframe", object_id="o", property="x", tick=1, value=2)
            self.assertEqual(len(r["electron"]["animation"]["keyframes"]), 1)
            self.assertEqual(r["electron"]["animation"]["keyframes"][0]["value"], 2)
            with self.assertRaises(ValueError):
                self.op("animation.keyframe", object_id="o", property="x", tick=2, value=3)
        finally:
            service_module.MAX_KEYFRAMES = old

    def test_ocr_commit_respects_object_limit(self):
        self.op("object.upsert", object_id="existing", object={})
        obs = self.op("ocr.observe", source_sha256="0" * 64, text="x", confidence=1, geometry={})["result"]["observation"]
        old = service_module.MAX_OBJECTS
        service_module.MAX_OBJECTS = 1
        try:
            with self.assertRaises(ValueError):
                self.op("ocr.commit", observation_id=obs["id"], object_id="new")
        finally:
            service_module.MAX_OBJECTS = old

    def test_empty_precondition_is_rejected_not_bypassed(self):
        with self.assertRaises(ValueError): self.op("suspend", expected_state_hash="")
        with self.assertRaises(ValueError): self.op("suspend", expected_state_hash=False)

    def test_rehashed_schema_invalid_state_is_rejected(self):
        p = self.svc.electrons_root / f"{self.e}.json"
        d = json.loads(p.read_text()); d["status"] = "BANANA"; refresh_hash(d); p.write_text(json.dumps(d))
        with self.assertRaises(ConflictError): self.svc.load(self.e)
        self.assertEqual(self.svc.list_electrons()[0]["integrity"], "SCHEMA_INVALID")

    def test_verify_all_detects_referenced_checkpoint_tamper(self):
        cp = self.op("checkpoint")["result"]["checkpoint"]
        path = self.svc.state_root / cp["relative_path"]
        d = json.loads(path.read_text()); d["name"] = "tampered"; path.write_text(json.dumps(d))
        report = self.svc.verify_all()
        self.assertFalse(report["ok"]); self.assertFalse(report["checks"]["checkpoints"]["ok"])

    def test_status_uses_cached_ledger_health_not_full_verify(self):
        self.svc.ledger.verify = lambda: (_ for _ in ()).throw(AssertionError("full verify called"))
        status = self.svc.status()
        self.assertTrue(status["ledger"]["ok"])

    def test_ocr_provenance_changes_observation_identity(self):
        base = dict(source_sha256="0" * 64, text="x", confidence=0.9, geometry={})
        a = self.op("ocr.observe", **base, engine="A")["result"]["observation"]
        b = self.op("ocr.observe", **base, engine="B")["result"]["observation"]
        self.assertNotEqual(a["id"], b["id"])

    def test_ocr_boolean_confidence_rejected(self):
        with self.assertRaises(ValueError):
            self.op("ocr.observe", source_sha256="0" * 64, text="x", confidence=True, geometry={})

    def test_fabric_diagnostic_enforces_capability(self):
        self.svc.security = SecurityPolicy(self.svc.state_root, capabilities=set())
        with self.assertRaises(SecurityError): self.svc.fabric_diagnostic()

    def test_verify_all_rejects_failed_fabric_attestation(self):
        class FailedFabric(FakeFabric):
            def attest(self, fresh=False):
                return {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 1, "nodes": {}, "error": "synthetic failure"}
        self.svc.fabric = FailedFabric(())
        report = self.svc.verify_all()
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["fabric"]["ok"])

    def test_clone_collision_is_conflict_and_preserves_existing_electron(self):
        import copy
        p = self.svc.load(self.e)
        counter = p["clone_counter"] + 1
        proposed = copy.deepcopy(p); proposed["clone_counter"] = counter; refresh_hash(proposed)
        clone_id = "e-" + sha256_json({"parent": self.e, "state_hash": proposed["state_hash"], "counter": counter})[:16]
        self.svc.create("victim", electron_id=clone_id)
        parent_before = self.svc.load(self.e)["state_hash"]
        with self.assertRaises(ConflictError):
            self.svc.clone(self.e)
        self.assertEqual(self.svc.load(clone_id)["name"], "victim")
        self.assertEqual(self.svc.load(self.e)["state_hash"], parent_before)

    def test_duplicate_persisted_state_keys_are_rejected(self):
        p = self.svc.electrons_root / f"{self.e}.json"
        text = p.read_text(encoding="utf-8")
        text = text.replace('  "name": "t",', '  "name": "evil",\n  "name": "t",', 1)
        p.write_text(text, encoding="utf-8")
        with self.assertRaises(ConflictError):
            self.svc.load(self.e)
        row = self.svc.list_electrons()[0]
        self.assertEqual(row["integrity"], "UNREADABLE")

    def test_checkpoint_metadata_tick_mismatch_fails_verification(self):
        cp = self.op("checkpoint")["result"]["checkpoint"]
        state = self.svc.load(self.e)
        state["checkpoints"][0]["tick"] += 1
        refresh_hash(state)
        self.svc._path(self.e).write_text(json.dumps(state), encoding="utf-8")
        report = self.svc.verify_all()
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["checkpoints"]["ok"])
        self.assertTrue(any("metadata tick" in e["error"] for e in report["checks"]["checkpoints"]["errors"]))

    def test_present_fabric_node_without_passing_checksum_fails_verification(self):
        class WeakFabric(FakeFabric):
            def attest(self, fresh=False):
                names = ("N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE")
                return {"schema": "DF/FABRIC_ATTEST/1", "_returncode": 0,
                        "nodes": {n: {"present": True, "bound": True, "sums_match": None} for n in names}}
        self.svc.fabric = WeakFabric()
        report = self.svc.verify_all()
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["fabric"]["ok"])
        self.assertIn("passing sealed checksum", report["checks"]["fabric"]["error"])

class LedgerAndModelTests(unittest.TestCase):
    def test_ledger_detects_out_of_band_tamper_before_append(self):
        with tempfile.TemporaryDirectory() as td:
            l = AppendOnlyLedger(Path(td) / "x.jsonl")
            l.append("e", 0, "a", {"x": 1}); l.append("e", 1, "b", {"x": 2})
            lines = l.path.read_text().splitlines()
            lines[0] = lines[0].replace('"x":1', '"x":9')
            l.path.write_text("\n".join(lines) + "\n")
            with self.assertRaises(LedgerIntegrityError): l.append("e", 2, "c", {})
    def test_ledger_rejects_duplicate_json_keys_even_when_effective_hash_matches(self):
        with tempfile.TemporaryDirectory() as td:
            l = AppendOnlyLedger(Path(td) / "x.jsonl")
            l.append("e", 0, "a", {"x": 1})
            text = l.path.read_text(encoding="utf-8")
            text = text.replace('"event_type":"a"', '"event_type":"evil","event_type":"a"', 1)
            l.path.write_text(text, encoding="utf-8")
            with self.assertRaises(LedgerIntegrityError):
                l.verify()

    def test_ledger_reopen_continues_chain(self):
        with tempfile.TemporaryDirectory() as td:
            AppendOnlyLedger(Path(td) / "x.jsonl").append("e", 0, "a", {})
            l2 = AppendOnlyLedger(Path(td) / "x.jsonl")
            self.assertEqual(l2.append("e", 1, "b", {})["seq"], 2)
            self.assertEqual(l2.verify()["events"], 2)
    def test_exact_and_step_interpolation(self):
        s = new_electron("e", "x")
        s["animation"]["keyframes"] = [
            {"id": "a", "object_id": "o", "property": "x", "tick": 0, "value": 0},
            {"id": "b", "object_id": "o", "property": "x", "tick": 3, "value": 1}]
        self.assertAlmostEqual(animation_value(s, "o", "x", 1), 1 / 3)
        self.assertIsInstance(animation_value(s, "o", "x", 3), int)
        s["animation"]["keyframes"][0]["interpolation"] = "step"
        self.assertEqual(animation_value(s, "o", "x", 2), 0)

    def test_ledger_tail_returns_latest_bounded_events(self):
        with tempfile.TemporaryDirectory() as td:
            l = AppendOnlyLedger(Path(td) / "x.jsonl")
            for i in range(20): l.append("e", i, "tick", {"i": i})
            tail = l.tail(5)
            self.assertEqual([e["payload"]["i"] for e in tail], [15, 16, 17, 18, 19])

    def test_ledger_tail_across_block_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            l = AppendOnlyLedger(Path(td) / "x.jsonl")
            for i in range(180): l.append("e", i, "tick", {"i": i, "text": "Δ" * 300})
            tail = l.tail(7)
            self.assertEqual([e["payload"]["i"] for e in tail], list(range(173, 180)))

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = Path(tempfile.mkdtemp()); (cls.td / "VEC1").mkdir()
        cls.svc = VECService(cls.td, fabric=FakeFabric())
        cls.httpd = vec_app.make_server(cls.svc, port=0, token="test-token")
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); shutil.rmtree(cls.td, ignore_errors=True)

    def req(self, method, path, body=None, headers=None, host=None, token="test-token"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        if body is not None:
            h["Content-Type"] = "application/json"
        if token: h["X-VEC1-Token"] = token
        h.update(headers or {})
        c.request(method, path, body=None if body is None else (body if isinstance(body, str) else json.dumps(body)), headers=h)
        r = c.getresponse(); data = r.read(); c.close()
        try: return r.status, json.loads(data)
        except ValueError: return r.status, data

    def test_index_carries_token_and_csp(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/", headers={"Host": f"127.0.0.1:{self.port}"}); r = c.getresponse(); body = r.read()
        self.assertEqual(r.status, 200); self.assertIn(b"test-token", body)
        self.assertIn("frame-ancestors 'none'", r.getheader("Content-Security-Policy"))
    def test_dns_rebinding_host_refused(self):
        self.assertEqual(self.req("GET", "/api/status", host="evil.example")[0], 421)
    def test_post_requires_token(self):
        self.assertEqual(self.req("POST", "/api/electrons", {"name": "x"}, token=None)[0], 403)
    def test_cross_origin_refused(self):
        self.assertEqual(self.req("POST", "/api/electrons", {"name": "x"}, headers={"Origin": "http://evil.example"})[0], 403)
    def test_simple_request_content_type_refused(self):
        self.assertEqual(self.req("POST", "/api/electrons", "{}", headers={"Content-Type": "text/plain"})[0], 415)
    def test_non_object_body_is_400(self):
        self.assertEqual(self.req("POST", "/api/electrons", "[1]")[0], 400)
    def test_duplicate_json_keys_are_rejected(self):
        st, data = self.req("POST", "/api/electrons", '{"name":"first","name":"second"}')
        self.assertEqual(st, 400); self.assertIn("duplicate JSON key", data["detail"])
    def test_nonstandard_nan_json_is_rejected(self):
        st, data = self.req("POST", "/api/electrons", '{"name":NaN}')
        self.assertEqual(st, 400); self.assertIn("non-finite JSON", data["detail"])
    def test_deeply_nested_json_is_rejected_as_bad_request(self):
        body = '{"x":' * 1100 + '0' + '}' * 1100
        st, data = self.req("POST", "/api/electrons", body)
        self.assertEqual(st, 400)
        self.assertTrue("nesting" in data["detail"] or "recursion" in data["detail"])

    def test_semantically_oversized_json_is_rejected_as_bad_request(self):
        body = '{"name":"' + ('a' * 1_100_000) + '"}'
        st, data = self.req("POST", "/api/electrons", body)
        self.assertEqual(st, 400)
        self.assertTrue("maximum" in data["detail"] or "exceeds" in data["detail"])

    def test_static_traversal_refused(self):
        self.assertEqual(self.req("GET", "/..%2f..%2fapp.py")[0], 404)
    def test_method_not_allowed(self):
        self.assertEqual(self.req("DELETE", "/api/electrons")[0], 405)
    def test_full_flow(self):
        st, e = self.req("POST", "/api/electrons", {"name": "<img src=x>"}); self.assertEqual(st, 201)
        eid = e["electron_id"]
        st, r = self.req("POST", f"/api/electrons/{eid}/operate", {"method": "object.upsert", "payload": {"object_id": "t", "object": {"text": "hi"}}})
        self.assertEqual(st, 200)
        st, r = self.req("POST", f"/api/electrons/{eid}/operate", {"method": "restore", "payload": {"checkpoint_hash": "../../x"}})
        self.assertEqual(st, 400)
        st, r = self.req("POST", f"/api/electrons/{eid}/operate", {"method": "cross_target.verify", "payload": {}})
        self.assertEqual(st, 200)
        self.assertEqual(self.req("GET", f"/api/electrons/nope")[0], 404)
        st, ev = self.req("GET", "/api/events?limit=5"); self.assertEqual(st, 200); self.assertLessEqual(len(ev["events"]), 5)

if __name__ == "__main__": unittest.main(verbosity=2)
