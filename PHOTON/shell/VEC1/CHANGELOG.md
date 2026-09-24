# VEC1 Changelog

## 0.6.0 — 2026-09-18 (Windows namespace, renderer isolation, JSON and schema hardening)

### Fixed
- Removed a real Windows case-insensitive extraction collision in the Xtra-Large evidence tree while preserving both provenance documents; dependent nested/Xtra-Large integrity metadata and DF_Fabric `N_XLARGE` seal pins are regenerated.
- Windows preflight now detects case-fold collisions, reserved device names, trailing-dot/space names, invalid Win32 filename characters, and control characters instead of reporting only path length.
- Normal renderer launch no longer falls back automatically to the user's ordinary default-browser profile; `--allow-default-browser-fallback` is now required for that compatibility path.
- HTTP mutation parsing uses the shared strict JSON parser, with a 4,000,000-byte raw-input ceiling and normalized recursion failure.
- API names, object/keyframe identifiers, OCR text/engine metadata, and OCR commit identifiers require real JSON strings instead of silent `str(...)` coercion.
- Xtra-Large nested release manifests are reconciled to the files actually delivered rather than stale historical bytecode entries.

### Tests / verification
- 72 → 80 tests; all 80 pass.
- Added Windows collision/reserved-name regressions, isolated-browser fallback policy tests, strict textual API tests, and deep/semantically oversized JSON HTTP tests.
- Xtra-Large G0 checksum/manifest/payload/core gates and associated schema/evidence/preflight/attestation boundary checks pass after canonicalization.

### Claim boundary
- Windows-native four-tier qualification remains NOT_RUN. Long relative paths remain and can still require a short extraction root/long-path-aware tooling. Full Electron parity, exhaustive workflow execution, production key custody/signing, external review, and long-duration soak remain outside the release claim.

## 0.5.0 — 2026-09-18 (sealed-runtime immutability, strict evidence, collision and concurrency hardening)

### Fixed
- Cross-target node execution and Fabric diagnostics now pass explicit temporary `--out` paths, preventing supplied adapters from writing `_runs/` artifacts into checksummed DF/Fabric baselines.
- Adapter subprocesses inherit `PYTHONDONTWRITEBYTECODE=1`, closing child-interpreter `.pyc` mutation of sealed VM trees.
- Deterministic clone IDs are collision-checked before the parent clone counter is committed; a collision raises a conflict without overwriting the existing electron or mutating the parent.
- Persisted electron/checkpoint/ledger/topology/adapter JSON rejects duplicate keys and non-finite numbers.
- Referenced checkpoint metadata must agree with the snapshot logical tick.
- Fabric attestation validates the documented schema, all four contract nodes, strict boolean semantics, bound=>present, and `sums_match: true` for every present node.
- Fabric diagnostics normalize to PASS only for zero exit, `CROSS_NODE_DIFFERENTIAL_AGREEMENT`, and `DETERMINISTIC_REPLAY_PASS`; unknown verdict strings fail closed.
- Normal shell startup takes a cross-platform advisory single-instance lock for `runtime_state`, preventing concurrent writers from two desktop shells.
- Direct `python VEC1/app.py` disables bytecode generation before runtime imports, preventing self-created unchecksummed `__pycache__` entries before the startup release gate.
- Release-manifest parsing rejects NaN/Infinity, validates checksum digest/version syntax, and converts version/checksum decoding failures into structured verification failures.
- Electron storage identity uses full regex matching; POSIX atomic state replacement now best-effort fsyncs the containing directory.

### Tests / live evidence
- 61 → 72 unit/integration/regression tests.
- Live locally bound Xtra-Large cross-target witness: PASS.
- Live Fabric diagnostic: PASS with deterministic replay.
- All five sealed DF/Fabric trees remained aggregate-byte identical before and after those live executions.

### Claim boundary
- Windows four-tier native qualification, full Electron parity, exhaustive workflow execution, external signing/review, long-duration soak, and full semantic lowering into every VM ISA remain outside this release.

## 0.4.0 — 2026-09-18 (semantic-state, Fabric, capability and startup-integrity hardening)

### Fixed
- Empty optimistic-concurrency hashes no longer bypass state preconditions; every supplied precondition must be a valid SHA-256.
- Persisted states are semantically validated on load/save/list/restore, so recomputing the outer hash cannot legitimize invalid lifecycle, lineage, object, keyframe, OCR, checkpoint or counter structure.
- Referenced checkpoints now participate in `verify_all`; corrupt or missing references fail the integrity sweep while orphan snapshots are reported for recovery.
- `witness_low64` now uses the actual low 64 bits of the SHA-256 digest rather than a 32-bit prefix.
- Fabric `require_all` counts only the four contract nodes, ignores unknown bound labels, and cross-target execution blocks on failed attestation.
- Nonzero/errored Fabric diagnostics force `FAIL`; the raw adapter verdict is retained only as diagnostic evidence.
- Explicitly empty capability sets remain deny-all; Fabric diagnostic and shutdown paths require capabilities; capability manifests include a canonical hash.
- HTTP JSON parsing rejects duplicate keys, NaN/Infinity and short bodies.
- Release verification validates manifest semantics, references and duplicate keys in addition to file hashes/counts.
- Normal startup verifies the static release before opening mutable state or binding the HTTP server.
- Windows/PowerShell launchers fall through incompatible Python candidates instead of stopping at the first command name found; Fabric diagnostic launch is fail-closed.
- Dashboard status uses cached ledger health; full ledger verification is streaming.
- Component-registry maturity is evidence-bounded instead of marking all 110 source concepts implemented.

### Tests
- 43 → 61 unit/integration/regression tests.
- Live local Xtra-Large adapter probe validates the corrected >32-bit low-64 witness path.

### Claim boundary
- Sealed DF trees remain baseline dependencies rather than VEC1-owned implementations. Windows four-tier native qualification, full Electron parity, exhaustive workflow execution, external signing/review, and full semantic VM lowering remain outside this release.

## 0.3.0 — 2026-09-18 (audit, correctness, release-integrity and Windows-launch hardening)

### Fixed
- `START_VEC1.cmd` now forwards `%*`; v0.2.0 documentation claimed argument forwarding but the `.cmd` launcher silently discarded `--port`, `--no-browser`, `--verify-only`, `--preflight`, and `--version`.
- OCR commit now enforces the same `MAX_OBJECTS` cap as direct object upsert; the previous path could create an additional object after the cap was reached.
- Keyframe updates at an existing `(object, property, tick)` are allowed at `MAX_KEYFRAMES`; only net-new keyframes are rejected at capacity.
- `cross_target.verify.require_all` now requires a real JSON boolean instead of Python truthiness (`"false"` no longer becomes true).
- Fabric attestation parse faults, malformed `nodes` output, and non-zero adapter exits now fail verification instead of being able to appear healthy.
- Renderer OCR selection state is cleared when changing electrons or restoring a checkpoint, preventing stale cross-electron observation IDs.

### Integrity / verification
- Added `runtime/release_integrity.py`: verifies `PACKAGE_SHA256SUMS.txt`, `RELEASE_MANIFEST.json`, release version/count/byte metadata, missing/unexpected static files, symlinks, and every inventoried SHA-256 while excluding only declared mutable runtime state.
- `--verify-only` now covers release files in addition to ledger/electron/Fabric runtime integrity.
- Added `--preflight`, `WINDOWS_CHECK.cmd`, and `WINDOWS_CHECK.ps1` for release verification, Python compatibility, and Windows path-risk reporting.
- Python 3.10+ is now explicitly checked by Windows, PowerShell and POSIX start/verify launchers; the source uses Python 3.10 syntax and previously only said “Python 3”.
- Added PowerShell verification launcher `VERIFY_VEC1.ps1`.

### Performance / robustness
- Event-ledger tail queries now read backward in bounded blocks instead of parsing the entire ledger on every dashboard refresh. Hash-chain verification behavior is preserved.
- Release preflight reports the longest sealed relative paths and the classic Win32 path budget. The DF trees are not renamed, preserving their sealed manifests/provenance.

### Tests
- 31 → 43 tests, adding release-integrity/tamper/unexpected-file/dynamic-state checks, Windows launcher contract, strict boolean handling, keyframe-at-cap replacement, OCR object-cap enforcement, Fabric failure propagation, and ledger tail block-boundary coverage.

### Still blocked / not claimed
- Full Electron API parity, full VEC semantic lowering into every VM ISA, Windows native build qualification for every VM, exhaustive 512,820-item workflow execution, production signing/key custody, external review, and long-duration soak remain outside this release.
- The sealed DF_Xtra_Large baseline still contains 253-character relative paths. Long-path-aware extraction or an extremely short Windows root is required; v0.3.0 surfaces this rather than mutating sealed baseline paths.

## 0.2.0 — 2026-09-16 (chop-shop overhaul)

Work order: `VEC1_Electron_Substitute-20260916` (GitHub Junkyard `_YARDOFFICE/work-orders`). No donor parts pulled from the yard; every change is build-new against the v0.1.0 baseline. DF_Small/Medium/Large/Xtra_Large/Fabric trees are **unchanged** (their sealed SHA256SUMS still match).

### Security (defects reproduced against v0.1.0 before fixing)
- **Checkpoint restore sandbox escape** — `restore` joined an unvalidated `checkpoint_hash` into a path (`../../secret/leak` read a file outside `checkpoints/`). Now SHA-256-validated, resolved through `safe_path`, content re-hashed, and electron identity checked.
- **DNS rebinding** — any `Host` header was served. Now only exact loopback authorities (HTTP 421 otherwise).
- **Cross-site requests** — a `text/plain` POST from any origin created electrons. POSTs now need `application/json`, a same-origin `Origin` (if sent) and the per-launch `X-VEC1-Token`.
- **Renderer XSS** — electron names/ids were written via `innerHTML` unescaped. All dynamic HTML is escaped.
- `object.upsert` let the body override `object_id`; fixed.
- Non-object JSON bodies produced HTTP 500; now 400. Unknown methods 400; security refusals 403; other verbs 405; request timeout 30 s; chunked bodies refused; internal error details no longer echoed.
- Extra headers: COOP, CORP, Permissions-Policy, `form-action 'none'`.
- Renderer launched with an isolated `--user-data-dir`, extensions disabled; Edge/Chrome/Chromium discovery on Windows, macOS and Linux (`VEC1_BROWSER` override).

### Correctness
- Lifecycle is enforced: SUSPENDED accepts only resume/retire/checkpoint/verify; RETIRED accepts only restore/verify and cannot be cloned; resume/suspend check the current status.
- Restore keeps checkpoint records taken after the restored snapshot and never lowers `clone_counter` (prevents clone-id reuse).
- `object.delete` drops the object's keyframes (previously left orphans).
- Animation interpolation is exact rational (`fractions.Fraction`); integral results stay `int`, so state hashes don't depend on float formatting. New `step` interpolation; invalid interpolation names rejected.
- Payloads pass canonical depth/size/finite-number limits before any mutation; per-electron caps on objects, keyframes and OCR observations; duplicate OCR observations at one tick → 409.
- Electron ids limited to `[A-Za-z0-9_-]{1,64}`; names ≤128 chars, no control characters; state files must match their own id.
- Cross-target verification reports `NOT_RUN` (not `FAIL`) when no node is bound.

### Robustness / performance
- Ledger caches its verified head: appends are O(1) instead of re-reading and re-verifying the whole file; any out-of-band file change forces full re-verification before the next append. Appends are fsynced.
- Fabric attestation cached for 5 s (v0.1.0 spawned a subprocess on every state operation); adapter timeouts/start failures return structured errors instead of HTTP 500.
- `--verify-only` performs a real sweep (ledger chain, every electron's state hash, fabric attestation) and exits 1 on failure (v0.1.0 always exited 0).
- `list_electrons` reports `HASH_MISMATCH`/`UNREADABLE` entries instead of silently hiding them; the UI badges them.
- Version comes from `VEC1/VERSION.txt` everywhere; `--version` flag; `/api/health`; `/api/events?limit=`; `POST /api/shutdown`; daemon request threads; port fallback binds atomically.

### Renderer
- Suspend / Resume / Retire controls and a checkpoint Restore picker; controls enable per lifecycle state.
- All handlers surface errors in the result pane; 409 conflicts auto-reload the electron.
- Keyboard-selectable electron cards, focus rings, `aria-live` status; newest ledger events first; interpolation selector.

### Launchers
- `START_VEC1.cmd/.ps1/.sh` forward arguments; POSIX scripts check for Python and exit 3 like the Windows ones.

### Tests
- 6 → 31 tests: service (traversal, tamper, lifecycle, restore merge, limits), ledger tamper/reopen, exact/step interpolation, and a live loopback HTTP suite (Host, Origin, token, content type, body shape, static traversal, 405, full flow).

### Not changed / still blocked
Claim boundary is unchanged: no Electron API parity, no full semantic lowering into every VM ISA, Windows native qualification NOT_RUN (this overhaul was verified on Linux, Python 3.11, headless Chromium).
