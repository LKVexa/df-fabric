from __future__ import annotations
import argparse, hmac, json, mimetypes, os, secrets, shutil, socket, subprocess, sys, threading, urllib.parse, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Keep direct `python VEC1/app.py` invocation from generating unchecksummed
# __pycache__ files before the startup release-integrity gate runs. Launchers
# also use -B, but the application enforces the invariant itself.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from runtime import VERSION
from runtime.service import VECService, ConflictError, NotFoundError
from runtime.ledger import LedgerIntegrityError
from runtime.security import SecurityError
from runtime.release_integrity import environment_preflight, verify_release
from runtime.instance_lock import SingleInstanceLock, InstanceLockError
from runtime.canonical import strict_json_loads

MAX_BODY = 2_000_000
REQUEST_TIMEOUT = 30
TOKEN_HEADER = "X-VEC1-Token"
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}

class HttpError(Exception):
    def __init__(self, status, error, detail=""):
        super().__init__(detail); self.status = status; self.error = error; self.detail = detail

class VECServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, addr, handler, service, token):
        super().__init__(addr, handler)
        self.service = service
        self.token = token
        port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.allowed_origins = {f"http://{h}" for h in self.allowed_hosts}

class Handler(BaseHTTPRequestHandler):
    server_version = f"VEC1/{VERSION}"
    sys_version = ""
    timeout = REQUEST_TIMEOUT

    @property
    def service(self) -> VECService:
        return self.server.service

    def log_message(self, fmt, *args):
        sys.stderr.write("[VEC1] " + fmt % args + "\n")

    # ---- response helpers ---------------------------------------------
    def _headers(self, status=200, ctype="application/json; charset=utf-8", length=None, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if length is not None: self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), usb=(), serial=(), hid=()")
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers()

    def _json(self, obj, status=200, extra=None):
        data = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        self._headers(status, length=len(data), extra=extra)
        if self.command != "HEAD": self.wfile.write(data)

    # ---- request guards -----------------------------------------------
    def _guard_host(self):
        """DNS-rebinding defence: a hostile page that rebinds its own name to
        127.0.0.1 still sends its own Host header, so only exact loopback
        authorities are served (v0.1.0 served any Host)."""
        host = (self.headers.get("Host") or "").strip().lower()
        if host not in self.server.allowed_hosts:
            raise HttpError(421, "misdirected request", "Host header is not this loopback shell")

    def _guard_mutation(self):
        """Cross-site request defence for state-changing calls: same-origin
        Origin (when sent), JSON content type, and the per-launch token that
        only the served renderer page knows."""
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self.server.allowed_origins:
            raise HttpError(403, "forbidden", "cross-origin request refused")
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise HttpError(415, "unsupported media type", "Content-Type must be application/json")
        supplied = self.headers.get(TOKEN_HEADER, "")
        if not hmac.compare_digest(supplied.encode(), self.server.token.encode()):
            raise HttpError(403, "forbidden", f"missing or invalid {TOKEN_HEADER}")

    def _read_json(self):
        raw_len = self.headers.get("Content-Length")
        if self.headers.get("Transfer-Encoding"):
            raise HttpError(411, "length required", "chunked bodies are not accepted")
        try:
            n = int(raw_len or "0")
        except ValueError:
            raise HttpError(400, "bad request", "invalid Content-Length")
        if n < 0 or n > MAX_BODY:
            raise HttpError(413, "payload too large", "request body too large")
        raw = self.rfile.read(n)
        if len(raw) != n:
            raise HttpError(400, "bad request", "request body ended before Content-Length bytes were received")
        body = strict_json_loads(raw) if raw else {}
        if not isinstance(body, dict):
            raise HttpError(400, "bad request", "request body must be a JSON object")
        return body

    # ---- static renderer ----------------------------------------------
    def _static(self, path):
        ui = (HERE / "ui").resolve()
        rel = "index.html" if path in ("/", "") else urllib.parse.unquote(path).lstrip("/")
        target = (ui / rel).resolve()
        if ui not in target.parents or not target.is_file():
            raise HttpError(404, "not found")
        data = target.read_bytes()
        if target.name == "index.html":
            data = data.replace(b"__VEC1_SESSION_TOKEN__", self.server.token.encode()).replace(b"__VEC1_VERSION__", VERSION.encode())
        ctype = STATIC_TYPES.get(target.suffix.lower()) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._headers(200, ctype, len(data))
        if self.command != "HEAD": self.wfile.write(data)

    def _dispatch(self, fn):
        try:
            self._guard_host()
            fn()
        except HttpError as e: self._json({"error": e.error, "detail": e.detail}, e.status)
        except NotFoundError as e: self._json({"error": "not found", "detail": str(e).strip("'")}, 404)
        except (ConflictError, LedgerIntegrityError) as e: self._json({"error": "integrity/conflict", "detail": str(e)}, 409)
        except SecurityError as e: self._json({"error": "security", "detail": str(e)}, 403)
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as e: self._json({"error": "bad request", "detail": str(e)}, 400)
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as e:
            self.log_message("internal error: %s: %s", type(e).__name__, e)
            self._json({"error": "internal error", "detail": type(e).__name__}, 500)

    def _get(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/health": return self._json({"ok": True, "version": VERSION})
        if p == "/api/status": return self._json(self.service.status())
        if p == "/api/topology": return self._json(self.service.fabric.topology())
        if p == "/api/electrons": return self._json({"electrons": self.service.list_electrons()})
        if p.startswith("/api/electrons/"):
            parts = [x for x in p.split("/") if x]
            if len(parts) != 3: raise HttpError(404, "not found")
            return self._json(self.service.load(parts[2]))
        if p == "/api/events":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._json({"events": self.service.ledger.tail(q.get("limit", ["250"])[0])})
        if p.startswith("/api/"): raise HttpError(404, "not found")
        return self._static(p)

    def _post(self):
        self._guard_mutation()
        p = urllib.parse.urlparse(self.path).path
        body = self._read_json()
        if p == "/api/electrons":
            return self._json(self.service.create(name=body.get("name", "Electron"), electron_id=body.get("electron_id")), 201)
        if p == "/api/fabric/diagnostic":
            return self._json(self.service.fabric_diagnostic())
        if p == "/api/shutdown":
            self.service.security.require("shell.shutdown")
            self._json({"ok": True, "detail": "shutting down"})
            threading.Thread(target=self.server.shutdown, daemon=True).start(); return
        parts = [x for x in p.split("/") if x]
        if len(parts) == 4 and parts[:2] == ["api", "electrons"] and parts[3] == "clone":
            return self._json(self.service.clone(parts[2], body.get("name")), 201)
        if len(parts) == 4 and parts[:2] == ["api", "electrons"] and parts[3] == "operate":
            payload = body.get("payload", {})
            if not isinstance(payload, dict): raise ValueError("payload must be object")
            return self._json(self.service.operate(parts[2], str(body.get("method", "")), payload))
        raise HttpError(404, "not found")

    def do_GET(self): self._dispatch(self._get)
    def do_HEAD(self): self._dispatch(self._get)
    def do_POST(self): self._dispatch(self._post)
    def _not_allowed(self): self._dispatch(lambda: (_ for _ in ()).throw(HttpError(405, "method not allowed")))
    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _not_allowed

def make_server(service, port=0, preferred=8765, token=None):
    token = token or secrets.token_urlsafe(32)
    ports = [port] if port else list(range(preferred, preferred + 30)) + [0]
    last = None
    for candidate in ports:
        try:
            return VECServer(("127.0.0.1", candidate), Handler, service, token)
        except OSError as e:
            last = e
    raise RuntimeError(f"no local port available: {last}")

def _browser_candidates():
    env = os.environ.get
    if os.name == "nt":
        roots = [env("ProgramFiles(x86)", ""), env("ProgramFiles", ""), env("LOCALAPPDATA", "")]
        rels = ["Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe", "Chromium/Application/chrome.exe"]
        return [Path(r) / rel for rel in rels for r in roots if r]
    if sys.platform == "darwin":
        return [Path(p) for p in ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                                  "/Applications/Chromium.app/Contents/MacOS/Chromium")]
    found = [shutil.which(n) for n in ("microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    return [Path(f) for f in found if f]

def launch_browser(url, profile_dir: Path, allow_default_fallback=False):
    """Launch an isolated Chromium-family app renderer when available.

    Falling back to the user's ordinary browser profile is opt-in because that
    profile can contain extensions, cookies and session state.  The VEC1 page
    carries a per-launch mutation token, so automatic launch must preserve the
    isolated-profile boundary by default.
    """
    override = os.environ.get("VEC1_BROWSER")
    candidates = ([Path(override)] if override else []) + _browser_candidates()
    for exe in candidates:
        if exe.is_file():
            try:
                profile_dir.mkdir(parents=True, exist_ok=True)
                subprocess.Popen([str(exe), f"--app={url}", f"--user-data-dir={profile_dir}", "--no-first-run",
                                  "--no-default-browser-check", "--disable-extensions", "--new-window"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return str(exe)
            except OSError:
                continue
    if allow_default_fallback:
        webbrowser.open(url, new=1)
        return "default-browser"
    return None

def _launch_browser_and_report(url, profile_dir: Path, allow_default_fallback=False):
    launched = launch_browser(url, profile_dir, allow_default_fallback=allow_default_fallback)
    if launched is None:
        print(
            "VEC1 renderer auto-launch skipped: no supported isolated Edge/Chrome/Chromium executable was found. "
            f"Open {url} manually, or restart with --allow-default-browser-fallback to opt into the ordinary browser profile.",
            file=sys.stderr, flush=True,
        )
    return launched

def verify_only():
    service = VECService(PACKAGE_ROOT)
    report = service.verify_all(include_release=True)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

def preflight_only():
    report = environment_preflight(PACKAGE_ROOT)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

def main(argv=None):
    ap = argparse.ArgumentParser(description=f"VEC1 Electron Substitute {VERSION} local reference shell")
    ap.add_argument("--host", default="127.0.0.1", help="loopback alias only (127.0.0.1 or localhost); listener remains IPv4 127.0.0.1")
    ap.add_argument("--port", type=int, default=0, help="fixed port; default picks 8765-8794")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--allow-default-browser-fallback", action="store_true", help="opt in to opening the shell in the ordinary default browser if no isolated Chromium-family renderer is found")
    ap.add_argument("--verify-only", action="store_true", help="runtime + release integrity sweep; exit 1 on any failure")
    ap.add_argument("--preflight", action="store_true", help="verify release, Python compatibility, and Windows path-risk profile")
    ap.add_argument("--version", action="version", version=VERSION)
    ns = ap.parse_args(argv)
    if ns.verify_only: return verify_only()
    if ns.preflight: return preflight_only()
    if ns.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("REFUSED: VEC1 reference shell may bind loopback only.")
    if not 0 <= ns.port <= 65535:
        raise SystemExit("REFUSED: port out of range.")
    release = verify_release(PACKAGE_ROOT)
    if not release.get("ok"):
        print("REFUSED: VEC1 release integrity verification failed before startup.", file=sys.stderr)
        print(json.dumps(release, indent=2), file=sys.stderr)
        return 4
    instance_lock = SingleInstanceLock(PACKAGE_ROOT / "VEC1" / "runtime_state" / ".vec1-shell.lock")
    try:
        instance_lock.acquire()
    except InstanceLockError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 5
    try:
        service = VECService(PACKAGE_ROOT)
        httpd = make_server(service, ns.port)
        url = f"http://127.0.0.1:{httpd.server_address[1]}/"
        print(f"VEC1 Electron Substitute v{VERSION} — loopback shell at {url}", flush=True)
        print("Network boundary: listener is 127.0.0.1 only; Host/Origin/token guarded; Ctrl+C stops the shell.", flush=True)
        if not ns.no_browser:
            threading.Timer(0.4, _launch_browser_and_report, args=(url, service.state_root / "browser_profile", ns.allow_default_browser_fallback)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
        return 0
    finally:
        instance_lock.release()

if __name__ == "__main__":
    raise SystemExit(main())
