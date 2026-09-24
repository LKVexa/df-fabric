#!/bin/sh
set -eu
cd "$(dirname "$0")"
find_python() {
  if [ -n "${PYTHON:-}" ]; then
    command -v "$PYTHON" >/dev/null 2>&1 && "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 && { PY="$PYTHON"; return 0; }
    return 1
  fi
  for candidate in python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 || continue
    PY="$candidate"; return 0
  done
  return 1
}
find_python || { echo "REFUSED: Python 3.10 or newer was not found on PATH." >&2; exit 3; }
exec "$PY" -B VEC1/app.py "$@"
