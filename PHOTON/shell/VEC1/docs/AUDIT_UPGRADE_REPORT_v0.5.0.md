# VEC1 Electron Substitute v0.5.0 — Audit, Parse, Upgrade & Hardening Report

**Audit date:** 2026-09-18  
**Input baseline:** `VEC1_Electron_Substitute_v0.4.0_Audited_Hardened(1).zip`  
**Baseline SHA-256:** `2c5343d1b5a293afde94f28a5030e2a4149d307f63e9fa3ea7c2ae1c7e8b2bfe`  
**Output:** VEC1 v0.5.0 candidate

## Executive result

The attached v0.4.0 baseline revalidated at 61/61 existing tests and matched the previously issued release hash. A third-pass adversarial audit reproduced additional execution-boundary, persistence, clone, Fabric-contract, and multi-instance defects not covered by v0.4.0. v0.5.0 repairs those issues without modifying any supplied DF/Fabric baseline file and expands the local regression suite to 72 tests.

The most important reproduced defect was self-mutation: a clean v0.4.0 release passed `verify_release`, then a successful locally bound Xtra-Large `cross_target.verify` created `DF_Xtra_Large/_runs/RUN_<timestamp>_n_xlarge.lctlc.json`; the same release then failed static verification because that file was unexpected. v0.5.0 routes adapter output to temporary paths and propagates no-bytecode-write policy to child Python processes. A live candidate probe verified that all five sealed DF/Fabric trees were byte-identical before and after both cross-target and Fabric diagnostic execution.

## Reproduced findings and dispositions

| ID | Severity | Reproduced condition | v0.5.0 disposition |
|---|---|---|---|
| VEC5-001 | Critical | `cross_target.verify` used adapter default `_runs/` output inside a sealed DF node. A clean release passed before the operation and failed release integrity afterward on the new run file. | **Fixed:** every node-run receives an explicit temporary `--out`; no adapter run record is written into a sealed tree. |
| VEC5-002 | High | `-B` applied only to the immediate adapter interpreter; child Python interpreters could still emit `.pyc` files inside sealed VM trees. | **Fixed:** adapter subprocesses inherit `PYTHONDONTWRITEBYTECODE=1`; live before/after tree digests remained identical. |
| VEC5-003 | High | Deterministic clone ID collision overwrote a pre-existing explicitly created electron with the predicted clone ID. | **Fixed:** clone ID is predicted from the would-be parent state and checked before committing the parent counter; collision raises `ConflictError` and preserves both states. |
| VEC5-004 | High | Persisted electron and ledger JSON accepted duplicate keys. A duplicate key could be inserted ahead of the effective last key while the canonical hash still verified. | **Fixed:** shared strict JSON parser rejects duplicate keys and non-finite numbers across state/checkpoints/ledger/topology/adapter evidence. |
| VEC5-005 | Medium | Current-state checkpoint metadata could claim a different tick from the referenced hash-valid snapshot and still pass `verify_checkpoints`. | **Fixed:** referenced checkpoint record tick must equal snapshot `logical_tick`. |
| VEC5-006 | High | `verify_all` accepted a present/bound Fabric node whose `sums_match` was missing/null because only explicit `False` was considered a checksum failure. | **Fixed:** present nodes require `sums_match is True`; attestation schema and boolean semantics are validated fail-closed. |
| VEC5-007 | Medium | A zero-exit Fabric diagnostic with arbitrary non-empty verdict such as `BANANA` surfaced that string as the wrapper verdict. | **Fixed:** wrapper emits `PASS` only for the documented agreement token plus deterministic replay token; otherwise `FAIL`. |
| VEC5-008 | High | Two normal shell launches could bind different loopback ports while sharing and concurrently writing one `runtime_state`. | **Fixed:** cross-platform advisory single-instance lock held for the lifetime of the normal shell. |
| VEC5-009 | Medium | Direct `python VEC1/app.py` without launcher `-B` could create unchecksummed VEC `__pycache__` files before the release gate and make startup refuse its own package. | **Fixed:** `app.py` disables bytecode writes before VEC runtime imports; launchers retain `-B`. |
| VEC5-010 | Medium | Release-manifest JSON still accepted Python's non-standard NaN/Infinity constants; invalid UTF-8 in `VERSION.txt` could escape the intended structured verifier path. | **Fixed:** strict manifest constants, checksum-digest syntax checks, semantic-version check, and structured version/checksum read failures. |
| VEC5-011 | Low | Internal electron path validation used regex `match` despite the state model using `fullmatch`. | **Fixed:** storage path identity now uses `fullmatch`. |
| VEC5-012 | Low | Atomic state replacement fsynced the file but not the containing directory on POSIX. | **Improved:** best-effort directory fsync after atomic replace. |

## Test and live execution evidence

- **72/72** Python unit/integration/regression tests pass.
- Existing Host/Origin/session-token, traversal, lifecycle, OCR, checkpoint, precondition, release-integrity, witness, and launcher regressions remain green.
- New regressions cover clone collision preservation, duplicate-key persisted state and ledger rejection, checkpoint-tick binding, present-node checksum fail-closed behavior, output-path routing, normalized diagnostic verdicts, non-finite release metadata, invalid UTF-8 version handling, direct-app bytecode suppression, and single-instance locking.
- Live cross-target probe: `N_XLARGE = PASS`; `N_SMALL/N_MEDIUM/N_LARGE = NOT_RUN` because they were present but not locally bound.
- Live Fabric diagnostic: normalized `PASS`, adapter verdict `CROSS_NODE_DIFFERENTIAL_AGREEMENT`, replay `DETERMINISTIC_REPLAY_PASS`, one participant.
- Five sealed trees remained aggregate-byte identical before/after the live v0.5.0 probe.
- Direct `python VEC1/app.py --preflight` without launcher `-B`: **PASS**, with zero VEC `__pycache__` directories afterward.
- Live two-process shell probe: first shell remained active; second shell was refused with exit code **5** by the runtime-state advisory lock.

## Preserved boundaries

No supplied file under `DF_Fabric`, `DF_Small`, `DF_Medium`, `DF_Large`, or `DF_Xtra_Large` is modified by the v0.5.0 source upgrade. Their embedded checksum inventories remain authoritative baseline evidence.

This release remains a local reference Electron substitute architecture, not a drop-in Electron implementation. Node.js/Electron API parity, full semantic lowering of object/animation/OCR operations into all four VM ISAs, Windows-native four-tier qualification, exhaustive 512,820-item workflow execution, production signing/key custody, external independent review, and long-duration soak are not claimed.

## Windows constraint

The sealed Xtra-Large baseline still contains relative paths up to 253 characters. This audit deliberately does not rename baseline paths. Use a long-path-aware extractor/Win32 long-path configuration or a very short extraction root and run `WINDOWS_CHECK.cmd` before startup.
