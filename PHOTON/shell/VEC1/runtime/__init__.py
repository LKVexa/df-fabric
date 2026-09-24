from pathlib import Path as _Path

def _read_version() -> str:
    try:
        return (_Path(__file__).resolve().parents[1] / "VERSION.txt").read_text(encoding="utf-8").strip() or "0.0.0"
    except (OSError, UnicodeError):
        return "0.0.0"

VERSION = _read_version()
