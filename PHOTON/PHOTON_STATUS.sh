#!/bin/sh
d=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$d/PHOTON_PYTHON.sh" "$d/PHOTON_STATUS.py" "$@"
