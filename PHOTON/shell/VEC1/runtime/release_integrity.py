from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

CHECKSUM_FILE = "PACKAGE_SHA256SUMS.txt"
RELEASE_MANIFEST = "RELEASE_MANIFEST.json"
DYNAMIC_PREFIX = "VEC1/runtime_state/"
EXCLUDED_STATIC = {CHECKSUM_FILE, RELEASE_MANIFEST}
EXPECTED_DYNAMIC_EXCLUSIONS = ["VEC1/runtime_state/**", CHECKSUM_FILE, RELEASE_MANIFEST]
EXPECTED_SCHEMA = "VEC1/RELEASE_MANIFEST/1"
EXPECTED_PRODUCT = "VEC1 Electron Substitute"
MAX_PATH_STRING = 259  # classic Win32 MAX_PATH minus the terminating NUL
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
WINDOWS_INVALID_CHARS = set('<>:"|?*')
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _reject_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out




def _reject_nonfinite_constant(value):
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _load_json_object(path: Path):
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return value


def _safe_manifest_path(raw: str) -> str:
    if not raw or "\\" in raw:
        raise ValueError("checksum paths must be non-empty canonical POSIX paths")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise ValueError(f"unsafe checksum path: {raw}")
    norm = p.as_posix()
    if norm in EXCLUDED_STATIC or norm.startswith(DYNAMIC_PREFIX):
        raise ValueError(f"checksum inventory includes an excluded path: {norm}")
    return norm


def _safe_reference_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError("release references must be non-empty canonical POSIX paths")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise ValueError(f"unsafe release reference: {raw}")
    return p.as_posix()


def _parse_checksum_inventory(path: Path):
    rows = []
    seen = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"malformed checksum line {line_no}")
        digest, raw_rel = parts[0].lower(), parts[1].strip()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"invalid SHA-256 at checksum line {line_no}")
        rel = _safe_manifest_path(raw_rel[1:] if raw_rel.startswith("*") else raw_rel)
        if rel in seen:
            raise ValueError(f"duplicate checksum path at line {line_no}: {rel}")
        seen.add(rel)
        rows.append((digest, rel))
    if not rows:
        raise ValueError("checksum inventory is empty")
    return rows


def _actual_static_files(root: Path):
    out = set()
    symlinks = []
    for p in root.rglob("*"):
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel in EXCLUDED_STATIC or rel.startswith(DYNAMIC_PREFIX):
            continue
        if p.is_symlink():
            symlinks.append(rel)
            continue
        if p.is_file():
            out.add(rel)
    return out, sorted(symlinks)


def windows_path_profile(package_root: Path, inventory_paths=None):
    root = Path(package_root).resolve()
    paths = list(inventory_paths or [])
    max_rel = max((len(p) for p in paths), default=0)
    longest = sorted((p for p in paths if len(p) == max_rel))[:5]

    # Windows' normal filesystem namespace is case-insensitive and rejects a
    # small set of device names / component spellings even when the ZIP format
    # itself can represent them.  Detect these before a release is promoted.
    folded = {}
    for rel in paths:
        folded.setdefault(rel.casefold(), []).append(rel)
    case_collisions = sorted(
        [sorted(set(group)) for group in folded.values() if len(set(group)) > 1],
        key=lambda group: group[0].casefold(),
    )
    invalid = []
    for rel in paths:
        for component in PurePosixPath(rel).parts:
            stem = component.rstrip(" .").split(".", 1)[0].upper()
            reasons = []
            if component.endswith((" ", ".")):
                reasons.append("trailing dot/space")
            if stem in WINDOWS_RESERVED:
                reasons.append("reserved device name")
            if any(ord(ch) < 32 or ch in WINDOWS_INVALID_CHARS for ch in component):
                reasons.append("invalid Windows character")
            if reasons:
                invalid.append({"path": rel, "component": component, "reasons": reasons})
    invalid.sort(key=lambda x: (x["path"].casefold(), x["component"].casefold()))

    # full path = root + separator + relative path. A value <=259 stays under
    # the classic Win32 string limit; shell/extractor limits can be stricter.
    max_root_chars = MAX_PATH_STRING - 1 - max_rel
    current_root_chars = len(str(root))
    current_full_max = current_root_chars + (1 if paths else 0) + max_rel
    namespace_ok = not case_collisions and not invalid
    return {
        "schema": "VEC1/WINDOWS_PATH_PROFILE/2",
        "max_relative_path_chars": max_rel,
        "longest_relative_paths": longest,
        "classic_max_path_string_chars": MAX_PATH_STRING,
        "classic_max_package_root_chars": max_root_chars,
        "current_package_root_chars": current_root_chars,
        "current_max_full_path_chars": current_full_max,
        "current_root_classic_compatible": (current_full_max <= MAX_PATH_STRING) if os.name == "nt" else None,
        "windows_namespace_compatible": namespace_ok,
        "case_insensitive_collisions": case_collisions,
        "invalid_windows_components": invalid[:100],
        "invalid_windows_component_count": len(invalid),
        "long_path_note": (
            "WindowsSafe-r1 canonicalization caps delivered relative paths at the release inventory maximum. "
            "For classic Win32 tooling, keep the extracted package root within classic_max_package_root_chars; a shorter root provides extra shell/tooling margin."
        ),
    }


def _validate_release_contract(root: Path, release: dict, rows, errors: list[str]):
    if release.get("schema") != EXPECTED_SCHEMA:
        errors.append(f"release manifest schema must be {EXPECTED_SCHEMA}")
    if release.get("product") != EXPECTED_PRODUCT:
        errors.append(f"release manifest product must be {EXPECTED_PRODUCT}")
    version = release.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("release manifest version is not a supported semantic version")
    if release.get("checksum_file") != CHECKSUM_FILE:
        errors.append(f"release manifest checksum_file must be {CHECKSUM_FILE}")
    if release.get("dynamic_exclusions") != EXPECTED_DYNAMIC_EXCLUSIONS:
        errors.append("release manifest dynamic_exclusions do not match the verifier contract")
    if isinstance(release.get("static_file_count"), bool) or not isinstance(release.get("static_file_count"), int) or release.get("static_file_count", -1) < 0:
        errors.append("release manifest static_file_count must be a non-negative integer")
    if isinstance(release.get("static_bytes"), bool) or not isinstance(release.get("static_bytes"), int) or release.get("static_bytes", -1) < 0:
        errors.append("release manifest static_bytes must be a non-negative integer")
    digest = release.get("checksum_file_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
        errors.append("release manifest checksum_file_sha256 must be 64 hexadecimal characters")

    entrypoints = release.get("entrypoints")
    if not isinstance(entrypoints, dict) or not entrypoints:
        errors.append("release manifest entrypoints must be a non-empty object")
    else:
        for key, raw in sorted(entrypoints.items()):
            try:
                rel = _safe_reference_path(raw)
                target = root / Path(*PurePosixPath(rel).parts)
                if not target.is_file():
                    errors.append(f"release entrypoint {key} is missing: {rel}")
            except Exception as e:
                errors.append(f"release entrypoint {key} invalid: {e}")

    for key, kind in (("build_status", "file"), ("audit_report", "file"), ("changelog", "file"), ("evidence", "dir")):
        raw = release.get(key)
        if raw is None:
            errors.append(f"release manifest missing {key}")
            continue
        try:
            rel = _safe_reference_path(raw)
            target = root / Path(*PurePosixPath(rel).parts)
            exists = target.is_file() if kind == "file" else target.is_dir()
            if not exists:
                errors.append(f"release reference {key} is missing: {rel}")
        except Exception as e:
            errors.append(f"release reference {key} invalid: {e}")

    # The static inventory is the file allowlist. References to static files must
    # be covered by it; otherwise the manifest could point verification/users at
    # an unchecksummed artifact.
    expected = {rel for _, rel in rows}
    for key in ("build_status", "audit_report", "changelog"):
        raw = release.get(key)
        if isinstance(raw, str):
            try:
                rel = _safe_reference_path(raw)
                if rel not in expected:
                    errors.append(f"release reference {key} is not in the checksum inventory: {rel}")
            except ValueError:
                pass
    if isinstance(entrypoints, dict):
        for key, raw in entrypoints.items():
            if isinstance(raw, str):
                try:
                    rel = _safe_reference_path(raw)
                    if rel not in expected:
                        errors.append(f"release entrypoint {key} is not in the checksum inventory: {rel}")
                except ValueError:
                    pass


def verify_release(package_root: Path):
    root = Path(package_root).resolve()
    report = {
        "schema": "VEC1/RELEASE_VERIFY/1",
        "ok": True,
        "package_root": str(root),
        "version": None,
        "files_expected": 0,
        "files_checked": 0,
        "bytes_checked": 0,
        "missing": [],
        "unexpected": [],
        "mismatches": [],
        "symlinks": [],
        "errors": [],
    }

    checksum_path = root / CHECKSUM_FILE
    manifest_path = root / RELEASE_MANIFEST
    version_path = root / "VEC1" / "VERSION.txt"
    if not checksum_path.is_file():
        report["errors"].append(f"missing {CHECKSUM_FILE}")
    if not manifest_path.is_file():
        report["errors"].append(f"missing {RELEASE_MANIFEST}")
    if not version_path.is_file():
        report["errors"].append("missing VEC1/VERSION.txt")
    if report["errors"]:
        report["ok"] = False
        return report

    try:
        release = _load_json_object(manifest_path)
        rows = _parse_checksum_inventory(checksum_path)
    except Exception as e:
        report["ok"] = False
        report["errors"].append(f"manifest parse failure: {type(e).__name__}: {e}")
        return report

    try:
        version = version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as e:
        report["ok"] = False
        report["errors"].append(f"version read failure: {type(e).__name__}: {e}")
        return report
    if not SEMVER.fullmatch(version):
        report["errors"].append("VEC1/VERSION.txt is not a supported semantic version")
    report["version"] = version
    report["files_expected"] = len(rows)
    expected = {rel for _, rel in rows}
    actual, symlinks = _actual_static_files(root)
    report["symlinks"] = symlinks
    report["missing"] = sorted(expected - actual)
    report["unexpected"] = sorted(actual - expected)

    _validate_release_contract(root, release, rows, report["errors"])

    try:
        checksum_digest = _sha256_file(checksum_path)
    except OSError as e:
        report["ok"] = False
        report["errors"].append(f"checksum inventory read failure: {type(e).__name__}: {e}")
        return report
    report["checksum_file_sha256"] = checksum_digest
    declared_value = release.get("checksum_file_sha256")
    declared_digest = declared_value.lower() if isinstance(declared_value, str) else ""
    if declared_digest != checksum_digest:
        report["errors"].append("RELEASE_MANIFEST checksum_file_sha256 does not match PACKAGE_SHA256SUMS.txt")
    if release.get("version") != version:
        report["errors"].append("release manifest version does not match VEC1/VERSION.txt")
    if release.get("static_file_count") != len(rows):
        report["errors"].append("release manifest static_file_count does not match checksum inventory")

    bytes_checked = 0
    mismatches = []
    for expected_digest, rel in rows:
        p = root / Path(*PurePosixPath(rel).parts)
        if rel not in actual:
            continue
        try:
            size = p.stat().st_size
            got = _sha256_file(p)
        except OSError as e:
            mismatches.append({"path": rel, "error": f"{type(e).__name__}: {e}"})
            continue
        bytes_checked += size
        report["files_checked"] += 1
        if got != expected_digest:
            mismatches.append({"path": rel, "expected": expected_digest, "actual": got})
    report["bytes_checked"] = bytes_checked
    report["mismatches"] = mismatches

    declared_bytes = release.get("static_bytes")
    if declared_bytes != bytes_checked and not report["missing"] and not mismatches:
        report["errors"].append("release manifest static_bytes does not match inventoried files")

    report["windows_path_profile"] = windows_path_profile(root, expected)
    if not report["windows_path_profile"].get("windows_namespace_compatible", False):
        report["errors"].append("static inventory is not compatible with the normal Windows case-insensitive filename namespace")
    report["ok"] = not (report["errors"] or report["missing"] or report["unexpected"] or report["mismatches"] or report["symlinks"])
    return report


def environment_preflight(package_root: Path):
    release = verify_release(package_root)
    py_ok = sys.version_info >= (3, 10)
    warnings = []
    profile = release.get("windows_path_profile") or {}
    if profile.get("max_relative_path_chars", 0) >= 240:
        warnings.append(profile.get("long_path_note"))
    if profile.get("case_insensitive_collisions"):
        warnings.append("Release contains case-insensitive path collisions that cannot be represented safely by the normal Windows filesystem namespace.")
    if profile.get("invalid_windows_component_count", 0):
        warnings.append("Release contains filename components that are invalid in the normal Windows filesystem namespace.")
    return {
        "schema": "VEC1/PREFLIGHT/2",
        "ok": bool(py_ok and release.get("ok") and profile.get("windows_namespace_compatible", False)),
        "version": release.get("version"),
        "python": {
            "version": ".".join(map(str, sys.version_info[:3])),
            "minimum": "3.10",
            "ok": py_ok,
            "executable": sys.executable,
        },
        "release": release,
        "warnings": [w for w in warnings if w],
    }
