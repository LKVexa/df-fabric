#!/bin/sh
# Resolve a Python 3.10+ interpreter, then run the requested Photon script.
set -e
if [ -n "${PYTHON:-}" ]; then exec "$PYTHON" -B "$@"; fi
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)' >/dev/null 2>&1; then
    exec "$c" -B "$@"
  fi
done
echo "[PHOTON] No Python 3.10+ interpreter found. Set PYTHON to an interpreter path." >&2
exit 127
