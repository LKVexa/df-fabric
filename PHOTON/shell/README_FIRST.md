# VEC1 Electron Substitute v0.6.0

This package is a **functional local reference implementation** of an Electron-style desktop application shell assembled around the supplied DF VM suite and DF_Fabric.

It does **not** replace Chromium with the DF VMs. It replaces Electron's bundled Node/main-process role with a deterministic VEC1 control plane, uses an installed Edge/Chrome/Chromium-family browser as the renderer, and routes state, policy, reference cross-target verification, and Fabric diagnostics through the VEC1/DF model.

## Start on Windows

1. Read `00_WINDOWS_EXTRACTION_README.txt` and use a short extraction root. Relative paths can still approach 253 characters.
2. Use Python **3.10 or newer**.
3. Run `WINDOWS_CHECK.cmd` after extraction. It verifies release integrity, Python compatibility, path-length risk, and Windows namespace safety (case collisions/reserved/invalid path components).
4. Double-click `START_VEC1.cmd`.

The Windows launchers test `py -3`, `python`, and `python3` in sequence and select the first interpreter that satisfies Python 3.10+. Start launchers forward command-line arguments including `--no-browser`, `--port N`, `--verify-only`, `--preflight`, and `--version`.

Normal startup is fail-closed on static release-integrity verification before mutable runtime state is opened or the loopback listener is created. It then acquires a single-instance lock for package runtime state.

By default the UI opens only in a discovered Edge/Chrome/Chromium-family executable using a dedicated VEC1 profile with extensions disabled. If no isolated renderer is available, VEC1 prints the loopback URL instead of silently opening the ordinary default browser. `--allow-default-browser-fallback` explicitly restores that weaker compatibility behavior.

## Verification

- `VERIFY_VEC1.cmd` — Windows test suite plus runtime/release integrity sweep.
- `VERIFY_VEC1.ps1` — PowerShell equivalent.
- `VERIFY_VEC1.sh` — POSIX equivalent.
- `START_VEC1.cmd --preflight` — static release verification + Python/Windows-path profile without starting the server.
- `FABRIC_DIAGNOSTIC.cmd` — Fabric attestation followed by deterministic diagnostic; fail-closed on failed gates.

`--verify-only` verifies the hash-chained ledger, strict persisted electron schema/hash invariants, referenced checkpoints, Fabric attestation/checksum records, and the immutable VEC1 release inventory.

## What changed in v0.6.0

See `VEC1/CHANGELOG.md`, `VEC1/docs/AUDIT_UPGRADE_REPORT_v0.6.0.md`, and `VEC1/docs/ARCHITECTURE_v0.6.0_ADDENDUM.md`.

Highlights:

- removed a Windows case-insensitive evidence filename collision in Xtra-Large without discarding either provenance document;
- regenerated the affected nested Xtra-Large release manifests/checksums and DF payload/inventory chain;
- Windows preflight now detects case-fold collisions and Win32-invalid/reserved path components and fails closed on namespace incompatibility;
- ordinary default-browser fallback is opt-in so the tokenized local shell does not silently reuse a normal browser profile/extensions/session state;
- HTTP and persistence use one strict JSON parser with a raw 4 MB ceiling plus semantic depth/item/string/canonical-size limits;
- API identifier/text fields reject non-string JSON values instead of coercing them;
- regression coverage increased from 72 to 80 tests.

## Implemented reference surfaces

- deterministic canonical electron state with semantic validation, strict persisted/request JSON, and SHA-256 identities;
- append-only hash-chained event ledger with fsynced append, strict line parsing, streaming full verification, cached health, and bounded tail reads;
- object edit/delete, state preconditions, rational-tick animation, OCR observation/explicit commit, clone lineage/collision protection, checkpoint/restore, lifecycle control;
- capability allowlist/hash, filesystem sandbox, loopback-only HTTP server with exact Host/Origin/token guards, and no VEC outbound-network or arbitrary host-execution facility;
- isolated local renderer launch, tier-aware placement, bounded witness lowering/normalization through supplied DF adapters;
- Fabric attestation and deterministic diagnostic execution with a validated fail-closed contract;
- execution-time protection of DF/Fabric baselines through explicit temporary adapter outputs and no-bytecode child environments;
- exact static release allowlist/SHA-256 verification and startup integrity gating;
- single-writer runtime-state locking for normal shell operation;
- local dashboard for inspector, lineage/state, topology, evidence, attestation, cross-target checks, and clone-lab workflows.

## Baseline/canonicalization note

`DF_Small`, `DF_Medium`, and `DF_Large` are byte-for-byte unchanged from the attached v0.5.0 package. `DF_Xtra_Large` is intentionally canonicalized for Windows: one colliding lowercase evidence filename is renamed with identical content and dependent integrity/evidence manifests are regenerated. `DF_Fabric` refreshes only the `N_XLARGE` seal pins and its dependent integrity metadata. No Xtra-Large execution source or Fabric/Xtra-Large adapter logic is changed by this packaging repair.

## Claim boundary

This remains **not a drop-in Electron API replacement**. It does not implement Node.js compatibility, native Electron modules, arbitrary preload scripts, BrowserWindow parity, tray/menu/dialog parity, or full lowering of VEC object/animation/OCR semantics into every VM ISA.

Windows native build qualification for every VM remains `NOT_RUN`. Long-path-aware extraction or a very short root may still be required because long relative paths remain. Exhaustive execution of the 512,820-item source workflow corpus, production signing/key custody, external review, and long-duration soak are not claimed.
