# VEC1 v0.5.0 Architecture Addendum

## Immutable execution boundary

v0.5.0 makes the sealed DF/Fabric trees an execution-time immutable boundary, not only a packaging-time promise. The v0.4.0 bridge invoked `node-run` and `fabric-run` without `--out`, so the supplied adapters used their default `_runs/` directories inside checksummed DF trees. A successful cross-target verification could therefore make the next release-integrity gate fail on an unexpected timestamped run record.

The v0.5.0 bridge always supplies an explicit temporary `--out` path for node and Fabric execution. It also sets `PYTHONDONTWRITEBYTECODE=1` in the adapter subprocess environment because Python's `-B` option applies only to the launched interpreter and is not automatically inherited by child interpreters. A live Xtra-Large/Fabric probe confirmed all five sealed trees remained aggregate-byte identical before and after execution.

## Strict evidence parsing

Integrity-bearing persisted JSON now uses a shared strict parser. Duplicate object keys and non-finite numbers are rejected before state, checkpoint, ledger, topology, or adapter evidence can be trusted. This closes an ambiguity where last-key-wins JSON could still reproduce the effective canonical hash while the underlying byte representation contained conflicting fields.

Release metadata also rejects non-standard `NaN`/`Infinity`, validates checksum digest syntax, and turns version decoding failures into structured release-verification failures.

## Clone and checkpoint integrity

Clone IDs remain deterministic, but a predicted clone ID is now checked before the parent clone counter is committed. If that ID already exists, cloning fails with a conflict and neither the existing electron nor the parent state is overwritten.

Referenced checkpoint metadata is now bound to the snapshot's own logical tick during full verification. Hash-valid checkpoint files with falsified current-state tick metadata no longer pass the checkpoint gate.

## Fabric contract validation

A valid Fabric attestation must use `DF/FABRIC_ATTEST/1`, contain all four contract node records, use real booleans for `present`/`bound`, never report a bound absent node, and report `sums_match: true` for every present node. Placement and quorum calculations count only records satisfying this contract.

Fabric diagnostic output is normalized to `PASS` only when the process exits zero, the adapter verdict is `CROSS_NODE_DIFFERENTIAL_AGREEMENT`, and replay reports `DETERMINISTIC_REPLAY_PASS`. Arbitrary truthy or unknown verdict strings fail closed.

## Single-instance shell

Normal desktop startup now acquires an advisory OS lock in `VEC1/runtime_state/.vec1-shell.lock`. A second shell pointed at the same runtime state exits before opening another writer. The lock file is dynamic state and remains outside the static release inventory. Verification/preflight commands remain usable without taking the shell lock.

## Direct Python invocation

`app.py` sets `sys.dont_write_bytecode = True` before importing VEC runtime modules. Official launchers still pass `-B`, but direct `python VEC1/app.py` execution can no longer create unchecksummed VEC `__pycache__` files before the startup integrity gate.

## Durability refinement

Atomic state writes continue to fsync the replacement file and now perform best-effort parent-directory fsync on POSIX after `os.replace`. Windows retains the existing file-fsync + atomic-replace path.
