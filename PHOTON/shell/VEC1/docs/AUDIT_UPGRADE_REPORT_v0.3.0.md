# VEC1 Electron Substitute v0.3.0 — Audit, Parse, Upgrade & Hardening Report

**Audit date:** 2026-09-18  
**Source:** `VEC1_Electron_Substitute_v0.2.0(1).zip`  
**Source SHA-256:** `53414b9205a6547193163c497daea9cd07fe48689556f130be2e487603bbf214`  
**Upgrade target:** `0.3.0`

## Executive result

The v0.2.0 baseline was structurally sound: the archive had 9,519 ZIP entries, 7,344 regular files, no ZIP traversal/symlink extraction hazards, all 7,342 inventoried static files matched `PACKAGE_SHA256SUMS.txt`, all 3,659 JSON files parsed, Python sources compiled, the existing 31 tests passed, and the baseline `--verify-only` sweep returned healthy state.

The audit nevertheless found launcher, integrity, correctness, verification, performance, and Windows-portability defects. v0.3.0 applies reversible fixes in the VEC1/root integration layer only. `DF_Fabric`, `DF_Small`, `DF_Medium`, `DF_Large`, and `DF_Xtra_Large` remain sealed and byte-preserved; their own checksum inventories still validate.

## Findings and disposition

| ID | Severity | Finding | v0.3.0 disposition |
|---|---|---|---|
| VEC3-001 | High | `START_VEC1.cmd` discarded all CLI arguments although v0.2.0 documentation claimed all launchers forwarded them. | **Fixed** with `%*`; regression test added. |
| VEC3-002 | High | `--verify-only` did not verify the immutable release checksum inventory, so source-file tamper/missing/unexpected files were outside the “integrity sweep.” | **Fixed** with full release verification and exact inventory comparison. |
| VEC3-003 | High | Fabric attestation could return malformed/parse-failed/nonzero output without necessarily making `verify_all()` fail. | **Fixed**; attestation is fail-closed for those conditions. |
| VEC3-004 | Medium | Runtime source requires Python 3.10 syntax but launch docs/checks only said “Python 3.” | **Fixed**; 3.10+ gate in start/verify launchers. |
| VEC3-005 | Medium | `ocr.commit` could create a new object after `MAX_OBJECTS` was reached. | **Fixed**; same cap enforced on every object-creation path. |
| VEC3-006 | Medium | At `MAX_KEYFRAMES`, replacing an existing keyframe was rejected despite no net growth. | **Fixed**; cap applies only to net-new keyframes. |
| VEC3-007 | Medium | `require_all` used Python truthiness; JSON string `"false"` evaluated true. | **Fixed**; strict JSON boolean required. |
| VEC3-008 | Medium | `/api/events?limit=N` still parsed the entire ledger on every refresh, undermining the O(1)-append performance work. | **Fixed**; reverse bounded-block tail reader. |
| VEC3-009 | Low | UI retained the last OCR observation ID when selecting another electron/restoring state. | **Fixed**; stale observation context cleared. |
| VEC3-010 | High portability risk | Sealed DF_Xtra_Large contains relative paths up to 253 characters; the old README's ordinary short-path example was not sufficient for classic Win32 path limits. | **Mitigated, not eliminated**: preflight/path profile + extraction note. Renaming sealed DF paths was deliberately refused because it would invalidate their manifests/provenance. |

## Release-integrity model added in v0.3.0

`runtime/release_integrity.py` treats `PACKAGE_SHA256SUMS.txt` as the static-file allowlist. Verification rejects malformed/unsafe/duplicate inventory paths, missing inventoried files, unexpected static files, symlinks in the static tree, checksum mismatches, release-version mismatch, checksum-file digest mismatch, count mismatch, and byte-count mismatch. `VEC1/runtime_state/**`, `PACKAGE_SHA256SUMS.txt`, and `RELEASE_MANIFEST.json` are the only intentional dynamic/self-referential exclusions.

## Windows path analysis

The longest sealed relative path is 253 characters. Using a classic 259-character Win32 path-string budget, this leaves at most 5 characters for the package root before the separator. That is why v0.3.0 does not claim generic “Windows-safe extraction” from Downloads/Desktop paths. `WINDOWS_CHECK.cmd` reports the actual profile after extraction. Long-path-aware extraction and Win32 long-path support are recommended. No DF baseline path was shortened or renamed.

## Verification gates for v0.3.0

The release gate requires: Python compile/import success; all unit/integration tests passing; `--preflight` release verification passing; `--verify-only` runtime + release verification passing; package checksum regeneration and self-verification; all five embedded DF/Fabric checksum inventories still passing; JSON parse sweep passing; no runtime-state or `__pycache__` artifacts included in the release; and ZIP CRC validation passing.

## Claim boundary

v0.3.0 remains a local engineering reference shell, not a drop-in Electron implementation and not a Windows-native certification. No claim is made that the 512,820 source workflow items were executed individually, that all four VM tiers were rebuilt on Windows, or that VEC object/animation/OCR semantics are fully lowered into every VM ISA.
