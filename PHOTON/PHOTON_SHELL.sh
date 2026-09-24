#!/bin/sh
d=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$d/PHOTON_PYTHON.sh" "$d/shell/VEC1/app.py" "$@"
