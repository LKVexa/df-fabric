"""Photon host bridge — UNBOUND vendored profile.

This module keeps the exact import surface of the DF host bridge that shipped
with VEC1 Electron Substitute 0.2.0 (``find_make``, ``find_sh``, ``run``,
``attest``, ``build_required``, ``fabric_run``) so that ``vec1/vecctl.py`` and
``vec1/core.py`` import and execute unchanged.

What it does NOT do is pretend to be bound to a host product. This Photon was
vendored into a product tree *unbound*: no adapter of the host product is
called, no node is reported as ``bound``, and no verdict is manufactured. Every
host surface returns a structured ``UNBOUND`` record, which propagates through
the existing fail-closed logic and lands as ``BLOCKED`` in ``vecctl doctor`` /
``vecctl verify``. That is the correct and intended state until somebody writes
a real bridge.

To bind this Photon to its host product, replace the four host functions below
(``find_make``, ``build_required``, ``attest``, ``fabric_run``) with calls into
the host product's own entry points. ``../../bridge/BRIDGE_CONTRACT.md`` states
the exact record shapes the control plane expects back.

Nothing here executes a subprocess. ``run`` is retained as a real, bounded
process runner because a future bound bridge needs it, but no code path in the
unbound profile calls it.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHOTON_ROOT = ROOT.parent                    # <product>/PHOTON
PROFILE = 'UNBOUND'
BRIDGE_SCHEMA = 'PHOTON/HOST_BRIDGE/1'

_UNBOUND_REASON = (
    'Photon vendored UNBOUND: no host-product adapter is wired into this bridge. '
    'See PHOTON/bridge/BRIDGE_CONTRACT.md.'
)


def _host_profile():
    """Read the per-product binding descriptor written at integration time."""
    p = ROOT / 'config' / 'photon_host.json'
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {'schema': 'PHOTON/HOST/1', 'host_product': 'UNKNOWN', 'bound': False}


def _unbound(op, extra=None):
    rec = {
        'schema': BRIDGE_SCHEMA,
        'bridge_profile': PROFILE,
        'operation': op,
        'bound': False,
        'status': 'UNBOUND',
        'verdict': 'BLOCKED',
        'returncode': 3,
        'reason': _UNBOUND_REASON,
        'host': _host_profile().get('host_product', 'UNKNOWN'),
        'nodes': {},
        'stdout': '',
        'stderr': _UNBOUND_REASON,
    }
    if extra:
        rec.update(extra)
    return rec


def _emit(op, out_path=None, extra=None):
    data = _unbound(op, extra)
    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + '.tmp')
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(tmp, out_path)
    runrec = {'argv': [], 'returncode': 3, 'stdout': '', 'stderr': _UNBOUND_REASON, 'unbound': True}
    return runrec, data


# ---- toolchain probes (host-neutral; safe to keep bound) -------------------------------------
def find_make():
    e = os.environ.get('DF_MAKE') or os.environ.get('PHOTON_MAKE')
    if e and (Path(e).exists() or shutil.which(e)):
        return e
    for name in ('make', 'mingw32-make', 'gmake'):
        p = shutil.which(name)
        if p:
            return p
    return None


def find_sh():
    return shutil.which('sh') or shutil.which('bash')


def _default_timeout():
    raw = os.environ.get('VEC1_TIMEOUT', '1800') or '1800'
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1800
    return min(max(value, 1), 86400)


DEFAULT_TIMEOUT = _default_timeout()


def run(argv, cwd=None, timeout=None):
    """Bounded process runner. Retained for a future bound bridge; unused while UNBOUND."""
    timeout = DEFAULT_TIMEOUT if timeout is None else int(timeout)
    if timeout < 1 or timeout > 86400:
        raise ValueError('timeout must be between 1 and 86400 seconds')
    env = os.environ.copy()
    sh = find_sh()
    if sh and os.name == 'nt':
        env.setdefault('SHELL', sh)
    argv = [str(x) for x in argv]
    try:
        p = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout, env=env)
    except subprocess.TimeoutExpired as e:
        return {'argv': argv, 'returncode': 124,
                'stdout': (e.stdout or '') if isinstance(e.stdout, str) else '',
                'stderr': f'timed out after {timeout}s', 'timed_out': True}
    except OSError as e:
        return {'argv': argv, 'returncode': 127, 'stdout': '', 'stderr': f'launch failed: {e}'}
    return {'argv': argv, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


# ---- host surfaces (UNBOUND) ------------------------------------------------------------------
def attest(out_path=None):
    """Host attestation. UNBOUND: returns an empty node table, so nothing binds."""
    return _emit('attest', out_path)


def build_required():
    """Host build. UNBOUND: reports blocked without invoking any toolchain."""
    rec = _unbound('build_required')
    rec['make'] = find_make()
    rec['ok'] = False
    rec['blocked'] = _UNBOUND_REASON
    return rec


def fabric_run(program, out_path, event_log_path=None, profile='single_process_deterministic',
               placement='static', strict=True, programs=None):
    """Host workload execution. UNBOUND: no verdict is produced, so promotion fails closed."""
    return _emit('fabric_run', out_path, {
        'program': str(program),
        'requested_profile': profile,
        'requested_placement': placement,
        'strict': bool(strict),
        'programs': programs,
        'event_log': str(event_log_path) if event_log_path else None,
    })
