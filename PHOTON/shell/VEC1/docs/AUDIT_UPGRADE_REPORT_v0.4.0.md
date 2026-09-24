# VEC1 Electron Substitute v0.4.0 — Audit, Parse, Upgrade & Hardening Report

**Audit date:** 2026-09-18  
**Baseline:** `VEC1_Electron_Substitute_v0.3.0_Audited_Hardened.zip`  
**Baseline SHA-256:** `839e1ed1e017ccdce58cb1f682a6925252213edf54f2c8fa99883ab87fa6f9bd`  
**Upgrade target:** `0.4.0`

## Executive result

The v0.3.0 baseline revalidated at 43/43 tests with runtime/Fabric/release verification healthy. A second-pass adversarial audit then reproduced additional semantic, integrity, capability, Fabric-quorum, request-parser, and launcher defects that the v0.3.0 checks did not cover. v0.4.0 repairs those defects in the VEC1/root integration layer and expands the regression suite to 61 tests before packaging.

`DF_Fabric`, `DF_Small`, `DF_Medium`, `DF_Large`, and `DF_Xtra_Large` are treated as sealed baselines and are not intentionally modified by this upgrade.

## Reproduced findings and disposition

| ID | Severity | Reproduced condition | v0.4.0 disposition |
|---|---|---|---|
| VEC4-001 | High | Empty/false optimistic-concurrency preconditions bypassed `_precondition` because presence was tested with truthiness. | **Fixed**: only `None` means absent; supplied values must be valid SHA-256. |
| VEC4-002 | High | A persisted state with an invalid lifecycle value was accepted if its outer state hash was recomputed. | **Fixed**: full semantic `validate_state` on load/save/list/restore. |
| VEC4-003 | High | `verify_all` did not validate the content/existence of checkpoints referenced by otherwise valid electron state. | **Fixed**: referenced checkpoint verification gate added. |
| VEC4-004 | Medium | `witness_low64` used the first 8 SHA-256 hex digits (32 bits). | **Fixed**: actual digest low 64 bits (last 16 hex digits). |
| VEC4-005 | High | `require_all` could be satisfied by four bound labels even when one was unknown and a required node was absent. | **Fixed**: only the four contract node identities count. |
| VEC4-006 | High | A nonzero Fabric diagnostic process could still surface a passing adapter verdict. | **Fixed**: process/parse faults force `FAIL`; raw adapter verdict retained separately. |
| VEC4-007 | High | Cross-target verification could proceed after a failed Fabric attestation if node-looking data was present. | **Fixed**: attestation error/nonzero exit blocks execution fail-closed. |
| VEC4-008 | High | `SecurityPolicy(capabilities=set())` expanded to default grants. | **Fixed**: explicit empty set is deny-all; capability manifest is hashed. |
| VEC4-009 | Medium | Direct Fabric diagnostic endpoint bypassed `SecurityPolicy`; shutdown had no capability gate. | **Fixed**: both operations require declared capabilities. |
| VEC4-010 | High | Release verification checked hashes/counts but did not validate key manifest semantics/references. | **Fixed**: exact schema/product/checksum/exclusion contract plus entrypoint/evidence/reference checks and duplicate-key rejection. |
| VEC4-011 | Medium | HTTP JSON accepted duplicate keys and Python's nonstandard NaN/Infinity constants. | **Fixed**: strict object parser rejects duplicates/non-finite constants and short bodies. |
| VEC4-012 | High | Normal app startup did not run static release verification. | **Fixed**: startup refuses before server creation when release verification fails. |
| VEC4-013 | Medium | Windows launcher selection stopped on an incompatible `py -3` even when another compatible Python executable could exist. | **Fixed**: candidate interpreters are compatibility-tested in order. |
| VEC4-014 | Medium | `FABRIC_DIAGNOSTIC.cmd` paused after attestation failure but continued to the next step and could exit misleadingly. | **Fixed**: first failed gate exits nonzero. |
| VEC4-015 | Medium | Dashboard status could trigger a full ledger verification on each refresh. | **Fixed**: cached ledger health with streaming full verification reserved for integrity gates/change detection. |
| VEC4-016 | Claim accuracy | Component registry labeled all 110 components `REFERENCE_IMPLEMENTED` regardless of dedicated executable evidence. | **Fixed**: evidence-bounded four-state maturity taxonomy. |

## Verification added

Regression coverage now explicitly tests precondition bypass, rehashed schema-invalid state, referenced checkpoint tamper, low-64 witness semantics, unknown Fabric node quorum, attestation fail-closed behavior, diagnostic return-code precedence, deny-all capability policy, OCR provenance identity, boolean confidence rejection, cached status health, duplicate/NaN HTTP JSON, release-manifest semantic tamper/duplicate keys, normal-startup fail-closed behavior, and launcher contracts.

A live adapter probe with the locally available bound `N_XLARGE` node accepts the new 64-bit witness and normalizes the exact value. Small/Medium/Large are present but not bound in this environment and are truthfully reported `NOT_RUN`; this does not constitute four-node requalification.

## Residual constraints / not claimed

- The in-package SHA-256 allowlist is an integrity mechanism, not an external authenticity signature.
- Mutable state update and ledger append are not a single transactional filesystem commit; a host crash or I/O failure between them can require recovery/reconciliation.
- Ledger cached-health change detection uses host file metadata as a fast invalidation signal; `--verify-only` performs the full streaming chain check.
- Windows-native build/launch qualification for every VM tier remains `NOT_RUN` in this environment.
- The sealed DF_Xtra_Large tree retains relative paths up to 253 characters.
- Full Electron API parity, complete VEC semantic lowering to every VM ISA, exhaustive 512,820-work-item execution, production signing/key custody, independent review, and long-duration soak are not claimed.
