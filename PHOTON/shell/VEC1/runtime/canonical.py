from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 1_000_000
MAX_INPUT_JSON_BYTES = 4_000_000
MAX_DEPTH = 32
MAX_ITEMS = 20000
MAX_STRING = 262144


def _validate(value: Any, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    if depth > MAX_DEPTH:
        raise ValueError("input exceeds maximum nesting depth")
    counter[0] += 1
    if counter[0] > MAX_ITEMS:
        raise ValueError("input exceeds maximum object/item count")
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numeric values are forbidden")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise ValueError("string exceeds maximum length")
        return
    if isinstance(value, list):
        for item in value:
            _validate(item, depth + 1, counter)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("object keys must be strings")
            _validate(k, depth + 1, counter)
            _validate(v, depth + 1, counter)
        return
    raise ValueError(f"unsupported JSON type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    _validate(value)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("canonical JSON exceeds maximum size")
    return text


def _reject_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_nonfinite_constant(value):
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def strict_json_loads(text: str | bytes):
    """Parse bounded JSON without duplicate keys or non-finite numbers.

    Persisted VEC1 state, ledger records, HTTP request bodies and adapter evidence
    are integrity-bearing data.  Bound the raw representation *before* parsing so
    a whitespace-heavy or intentionally malformed local file cannot force an
    unbounded allocation.  `canonical_json` then enforces the semantic
    depth/item/string/finite/canonical-size limits used for writes and hashes.
    """
    if isinstance(text, bytes):
        raw_size = len(text)
        if raw_size > MAX_INPUT_JSON_BYTES:
            raise ValueError(f"JSON input exceeds maximum size ({MAX_INPUT_JSON_BYTES} bytes)")
        text = text.decode("utf-8")
    elif isinstance(text, str):
        raw_size = len(text.encode("utf-8"))
        if raw_size > MAX_INPUT_JSON_BYTES:
            raise ValueError(f"JSON input exceeds maximum size ({MAX_INPUT_JSON_BYTES} bytes)")
    else:
        raise TypeError("JSON input must be text or UTF-8 bytes")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except RecursionError as e:
        raise ValueError("JSON nesting exceeds parser recursion limit") from e
    canonical_json(value)
    return value


def strict_json_load(path: Path):
    return strict_json_loads(Path(path).read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def atomic_write_json(path, value: Any) -> None:
    import os, tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Validate with the same canonical policy used by hashing before opening the
    # destination.  The pretty representation is for human inspection only.
    canonical_json(value)
    data = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        # Best-effort directory durability on POSIX. Windows does not expose a
        # portable directory fsync through Python; file fsync + replace remains
        # the supported path there.
        if os.name != "nt":
            try:
                dfd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError:
                pass
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass
