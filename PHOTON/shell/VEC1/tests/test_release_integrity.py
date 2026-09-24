import hashlib, json, shutil, tempfile, unittest, sys
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
VEC = HERE.parents[1]
ROOT = VEC.parent
sys.path.insert(0, str(VEC))
from runtime.release_integrity import verify_release, windows_path_profile
import app as vec_app


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleaseIntegrityTests(unittest.TestCase):
    def fixture(self):
        td = Path(tempfile.mkdtemp())
        (td / "VEC1" / "docs").mkdir(parents=True)
        (td / "VEC1" / "evidence").mkdir(parents=True)
        (td / "VEC1" / "VERSION.txt").write_text("9.9.9\n", encoding="utf-8")
        (td / "payload.txt").write_text("payload\n", encoding="utf-8")
        (td / "START_VEC1.cmd").write_text("@echo off\n", encoding="utf-8")
        (td / "VEC1" / "BUILD_STATUS.json").write_text("{}\n", encoding="utf-8")
        (td / "VEC1" / "docs" / "AUDIT.md").write_text("audit\n", encoding="utf-8")
        (td / "CHANGELOG.md").write_text("changes\n", encoding="utf-8")
        files = [
            "VEC1/VERSION.txt", "payload.txt", "START_VEC1.cmd",
            "VEC1/BUILD_STATUS.json", "VEC1/docs/AUDIT.md", "CHANGELOG.md",
        ]
        sums = "".join(f"{sha(td / rel)}  {rel}\n" for rel in files)
        (td / "PACKAGE_SHA256SUMS.txt").write_text(sums, encoding="utf-8")
        manifest = {
            "schema": "VEC1/RELEASE_MANIFEST/1",
            "product": "VEC1 Electron Substitute",
            "version": "9.9.9",
            "static_file_count": len(files),
            "static_bytes": sum((td / rel).stat().st_size for rel in files),
            "checksum_file": "PACKAGE_SHA256SUMS.txt",
            "checksum_file_sha256": sha(td / "PACKAGE_SHA256SUMS.txt"),
            "dynamic_exclusions": ["VEC1/runtime_state/**", "PACKAGE_SHA256SUMS.txt", "RELEASE_MANIFEST.json"],
            "entrypoints": {"windows_cmd": "START_VEC1.cmd"},
            "build_status": "VEC1/BUILD_STATUS.json",
            "audit_report": "VEC1/docs/AUDIT.md",
            "changelog": "CHANGELOG.md",
            "evidence": "VEC1/evidence",
        }
        (td / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        return td

    def test_valid_release_passes(self):
        r = verify_release(self.fixture())
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["files_checked"], 6)

    def test_tamper_is_detected(self):
        td = self.fixture(); (td / "payload.txt").write_text("tampered\n", encoding="utf-8")
        r = verify_release(td)
        self.assertFalse(r["ok"]); self.assertEqual(r["mismatches"][0]["path"], "payload.txt")

    def test_unexpected_static_file_is_detected(self):
        td = self.fixture(); (td / "extra.txt").write_text("x", encoding="utf-8")
        r = verify_release(td)
        self.assertFalse(r["ok"]); self.assertIn("extra.txt", r["unexpected"])

    def test_runtime_state_is_dynamic(self):
        td = self.fixture(); p = td / "VEC1" / "runtime_state" / "x.json"; p.parent.mkdir(); p.write_text("{}")
        self.assertTrue(verify_release(td)["ok"])

    def test_manifest_semantic_tamper_is_detected(self):
        td = self.fixture(); p = td / "RELEASE_MANIFEST.json"; m = json.loads(p.read_text())
        m["schema"] = "EVIL/SCHEMA"; m["checksum_file"] = "NOT_THE_FILE"; m["dynamic_exclusions"] = []
        p.write_text(json.dumps(m), encoding="utf-8")
        r = verify_release(td)
        self.assertFalse(r["ok"])
        self.assertTrue(any("schema" in e for e in r["errors"]))
        self.assertTrue(any("checksum_file" in e for e in r["errors"]))

    def test_duplicate_manifest_keys_are_rejected(self):
        td = self.fixture(); p = td / "RELEASE_MANIFEST.json"
        raw = p.read_text(encoding="utf-8").rstrip("}") + ',"version":"1.2.3"}'
        p.write_text(raw, encoding="utf-8")
        r = verify_release(td)
        self.assertFalse(r["ok"])
        self.assertTrue(any("duplicate JSON key" in e for e in r["errors"]))

    def test_nonfinite_manifest_json_is_rejected(self):
        td = self.fixture(); p = td / "RELEASE_MANIFEST.json"
        raw = p.read_text(encoding="utf-8").rstrip("}") + ',"nonstandard":NaN}'
        p.write_text(raw, encoding="utf-8")
        r = verify_release(td)
        self.assertFalse(r["ok"])
        self.assertTrue(any("non-finite JSON number" in e for e in r["errors"]))

    def test_invalid_utf8_version_returns_structured_failure(self):
        td = self.fixture(); (td / "VEC1" / "VERSION.txt").write_bytes(b"\xff\xfe")
        r = verify_release(td)
        self.assertFalse(r["ok"])
        self.assertTrue(any("version read failure" in e for e in r["errors"]))

    def test_windows_path_profile_reports_budget(self):
        p = windows_path_profile(Path("."), ["a" * 253])
        self.assertEqual(p["max_relative_path_chars"], 253)
        self.assertEqual(p["classic_max_package_root_chars"], 5)


    def test_windows_path_profile_detects_case_collision(self):
        p = windows_path_profile(Path("."), ["Dir/INPUT.json", "dir/input.json"])
        self.assertFalse(p["windows_namespace_compatible"])
        self.assertEqual(len(p["case_insensitive_collisions"]), 1)

    def test_windows_path_profile_detects_reserved_component(self):
        p = windows_path_profile(Path("."), ["safe/CON.txt"])
        self.assertFalse(p["windows_namespace_compatible"])
        self.assertEqual(p["invalid_windows_component_count"], 1)

    def test_browser_default_profile_fallback_is_opt_in(self):
        with mock.patch.object(vec_app, "_browser_candidates", return_value=[]), \
             mock.patch.dict(vec_app.os.environ, {}, clear=False), \
             mock.patch.object(vec_app.webbrowser, "open") as browser_open:
            vec_app.os.environ.pop("VEC1_BROWSER", None)
            with tempfile.TemporaryDirectory() as td:
                launched = vec_app.launch_browser("http://127.0.0.1:1/", Path(td))
        self.assertIsNone(launched)
        browser_open.assert_not_called()

    def test_browser_default_profile_fallback_can_be_explicitly_enabled(self):
        with mock.patch.object(vec_app, "_browser_candidates", return_value=[]), \
             mock.patch.dict(vec_app.os.environ, {}, clear=False), \
             mock.patch.object(vec_app.webbrowser, "open", return_value=True) as browser_open:
            vec_app.os.environ.pop("VEC1_BROWSER", None)
            with tempfile.TemporaryDirectory() as td:
                launched = vec_app.launch_browser("http://127.0.0.1:1/", Path(td), allow_default_fallback=True)
        self.assertEqual(launched, "default-browser")
        browser_open.assert_called_once()

    def test_windows_cmd_forwards_arguments_and_has_fallbacks(self):
        text = (ROOT / "START_VEC1.cmd").read_text(encoding="utf-8")
        self.assertIn("VEC1\\app.py %*", text)
        self.assertIn("where py", text)
        self.assertIn("where python", text)
        self.assertIn("where python3", text)
        self.assertLess(text.index("where py"), text.index("where python"))

    def test_app_self_disables_bytecode_before_runtime_imports(self):
        text = (ROOT / "VEC1" / "app.py").read_text(encoding="utf-8")
        self.assertIn("sys.dont_write_bytecode = True", text)
        self.assertLess(text.index("sys.dont_write_bytecode = True"), text.index("from runtime import VERSION"))

    def test_fabric_cmd_is_fail_closed(self):
        text = (ROOT / "FABRIC_DIAGNOSTIC.cmd").read_text(encoding="utf-8")
        self.assertIn("fabric-attest", text)
        self.assertIn("if errorlevel 1 goto :fail", text)
        self.assertIn("exit /b 1", text)

    def test_normal_startup_fails_closed_on_release_integrity(self):
        with mock.patch.object(vec_app, "verify_release", return_value={"ok": False, "errors": ["synthetic"]}), \
             mock.patch.object(vec_app, "make_server") as make_server:
            rc = vec_app.main(["--no-browser"])
        self.assertEqual(rc, 4)
        make_server.assert_not_called()


if __name__ == "__main__": unittest.main(verbosity=2)
