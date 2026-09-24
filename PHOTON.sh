#!/bin/sh
# Photon dispatch.  Usage:  ./PHOTON.sh [status|ctl|shell] [args...]
d=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cmd=${1:-status}; [ $# -gt 0 ] && shift
case "$cmd" in
  status) exec sh "$d/PHOTON/PHOTON_STATUS.sh" "$@" ;;
  ctl)    exec sh "$d/PHOTON/PHOTON_CTL.sh" "$@" ;;
  shell)  exec sh "$d/PHOTON/PHOTON_SHELL.sh" "$@" ;;
  *) echo "[PHOTON] Unknown command '$cmd'.  Use: status | ctl | shell" >&2; exit 2 ;;
esac
