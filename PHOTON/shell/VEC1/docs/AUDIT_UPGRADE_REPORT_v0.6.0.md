# VEC1 Electron Substitute v0.6.0 — Audit, Upgrade, Hardening & Windows-Portability Report

**Audit date:** 2026-09-18  
**Input baseline:** `VEC1_Electron_Substitute_v0.5.0_Audited_Hardened(4).zip`  
**Baseline SHA-256:** `b58b42733bbaf40c7c93d640ef03da86528f53142ccc76e56fcfb0e9aa11f4a2`  
**Output:** VEC1 v0.6.0 audited/hardened candidate

## Executive result

The attached v0.5.0 baseline passed its existing 72-test VEC1 regression suite. A new packaging/runtime-boundary audit found a Windows extraction defect that the prior preflight did not model: the Xtra-Large VM contained two distinct evidence files whose paths differ only by case (`INPUT_PROVENANCE.json` and `input_provenance.json`). On a case-insensitive Windows filesystem, those names alias the same target and can overwrite one another during extraction.

v0.6.0 removes that ambiguity without dropping evidence. The lowercase 584-byte record is preserved byte-for-byte (SHA-256 `81d3dff99e186f355c2036c5300506e01083793bb434b8809a247669e8bde108`) as `INPUT_PROVENANCE_GUIDANCE.json`; the uppercase authority record remains untouched. Dependent Xtra-Large release manifests, SHA inventories, payload digest, and package manifest are regenerated and the Xtra-Large G0 integrity battery passes.

The audit also tightened renderer isolation, JSON ingestion, and service schema enforcement. The regression suite is expanded to **80 tests**, all passing.

## Findings and dispositions

| ID | Severity | Reproduced condition | v0.6.0 disposition |
|---|---|---|---|
| VEC6-001 | High | The ZIP contains two different Xtra-Large evidence files whose names differ only by case. Windows case-insensitive extraction can alias/overwrite them. | **Fixed:** preserve the lowercase file bytes under the unique `INPUT_PROVENANCE_GUIDANCE.json` name; rebuild every dependent nested/outer integrity record. |
| VEC6-002 | High | The v0.5 Windows preflight reported path length but did not detect case-insensitive namespace collisions, reserved device names, trailing-dot/space components, or invalid Win32 filename characters. | **Fixed:** Windows path profile schema v2 detects collision groups and invalid components; preflight fails closed when the static namespace is not Windows compatible. |
| VEC6-003 | Medium | If no Edge/Chrome/Chromium app-mode executable is found, the shell automatically called the OS default browser. That can reuse a normal user profile with extensions/session state around a URL containing the per-launch shell token. | **Fixed:** isolated Chromium-family app mode is the default boundary. Ordinary default-browser fallback is disabled unless the operator explicitly passes `--allow-default-browser-fallback`. |
| VEC6-004 | Medium | Strict JSON semantics existed, but the shared parser had no raw-byte ceiling before parsing and a pathological nesting level could surface parser recursion separately from the normal validation path. | **Fixed:** raw JSON is capped at 4,000,000 UTF-8 bytes before parse; parser recursion is normalized to `ValueError`; semantic depth/item/string/canonical-size checks remain enforced. |
| VEC6-005 | Medium | The HTTP layer maintained a second JSON parser instead of using the persistence parser, increasing boundary drift risk. | **Fixed:** HTTP request parsing now delegates to the same shared strict parser used by integrity-bearing state. |
| VEC6-006 | Medium | Several API identifiers/text fields were coerced with `str(...)`, so JSON numbers/booleans could silently become textual names, object IDs, or OCR engine/text values. | **Fixed:** those fields now require actual JSON strings and use bounded/control-character validation. |
| VEC6-007 | Medium | The Xtra-Large nested world/VM release manifests in the supplied archive referenced older CPython 3.11 bytecode that was absent while current CPython 3.13 cache files were present but unlisted. | **Fixed:** affected nested release manifests are regenerated from the delivered tree and their manifest SHA sidecars are refreshed. Outer DF inventory rules remain unchanged. |

## Xtra-Large canonicalization scope

The v0.6.0 upgrade deliberately changes only Xtra-Large evidence/integrity metadata required to make the package Windows-safe:

- renamed: `vm/QUORUM_LCTL_MSSL_2.1.0/vm/world/evidence/input_provenance.json` → `.../INPUT_PROVENANCE_GUIDANCE.json`;
- regenerated: world `evidence/RELEASE_MANIFEST.json` + `.sha256`;
- regenerated: VM `vm/evidence/RELEASE_MANIFEST.json` + `.sha256`;
- regenerated: embedded VM `SHA256SUMS.txt`;
- regenerated: `node/PAYLOAD_DIGEST.json`;
- regenerated: Xtra-Large `MANIFEST.json` and `SHA256SUMS.txt`;
- refreshed downstream DF_Fabric `N_XLARGE` checksum/manifest/payload pins and regenerated Fabric integrity metadata.

`DF_Small`, `DF_Medium`, and `DF_Large` remain byte-for-byte identical to the attached v0.5.0 archive. `DF_Fabric` changes only its `N_XLARGE` registry pins plus dependent `MANIFEST.json`/`SHA256SUMS.txt`, so Fabric continues to fail closed against the newly canonicalized Xtra-Large seal. No Fabric adapter source or Xtra-Large executable VM/adapter source, runtime implementation, key material, or scenario content is rewritten by the canonicalization.

## Verification evidence

- Existing baseline before changes: **72/72 tests PASS**.
- Hardened v0.6.0 VEC1 suite: **80/80 tests PASS**.
- New regressions cover case-insensitive Windows collisions, reserved Win32 components, default-browser fallback opt-in, raw/deep/semantic JSON rejection, and strict string typing for names/object/OCR fields.
- Xtra-Large adapter verification completed G0.1 checksum inventory, G0.2 manifest inventory, G0.3 embedded payload digest, G0.4 core digest, JSON-schema evidence, evidence citation, reference core, toolchain preflight, attestation boundary, and physical-claim firewall gates successfully. A longer adapter battery was not used as a release claim after the tool execution window elapsed.
- Full final VEC1 release inventory/preflight/verify results are recorded in `VEC1/evidence` in this candidate.

## Remaining constraints / claim boundary

VEC1 remains a local reference Electron-substitute architecture, not a drop-in Electron API implementation. It does not claim Node.js compatibility, Electron native-module compatibility, arbitrary preload execution, BrowserWindow/tray/menu/dialog parity, or complete semantic lowering of all VEC object/animation/OCR operations into every VM ISA.

Windows-native execution/build qualification of every VM tier is **NOT_RUN** in this audit. WindowsSafe-r1 canonicalization reduces the delivered relative-path ceiling to 156 characters, removes redundant duplicate workflow directories, and leaves approximately 102 characters of classic Win32 package-root budget. A package root of 90 characters or fewer is recommended for additional tooling margin. Exhaustive 512,820-item workflow execution, production signing/key custody, external independent review, and long-duration soak are not claimed.
