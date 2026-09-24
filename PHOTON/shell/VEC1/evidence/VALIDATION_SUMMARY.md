# VEC1 v0.1.0 Validation Summary

## PASS evidence

- **Baseline preservation:** every file payload from the five supplied DF/Fabric ZIPs matches the corresponding integrated-package file by SHA-256 (`BASELINE_PRESERVATION_VALIDATION.json`).
- **Four-node build:** DF_Small, DF_Medium, DF_Large, and DF_Xtra_Large were built in an isolated validation copy (`FOUR_NODE_BUILD_VALIDATION.json`).
- **Fabric federation:** the supplied Bell-pair diagnostic ran with all four nodes bound, cross-node differential agreement, and deterministic replay (`FABRIC_VALIDATION.json`).
- **Cross-target VEC witness:** one canonical VEC payload witness was lowered to Small/MSSL, Medium/LCTLC/1.1, Large/LCTLC/1.2, and Xtra-Large/LCTLC/QVM and normalized to the same value on all four targets (`CROSS_TARGET_WITNESS_VALIDATION.json`).
- **Local unit suite:** all six VEC1 unit tests passed (`LOCAL_TEST_RESULTS.json`).
- **HTTP/state integration:** renderer shell, state creation, object edit, animation, OCR bridge/commit, checkpoint, clone, degraded cross-target verification, Fabric diagnostic, ledger, and state readback passed (`HTTP_INTEGRATION_TEST.json`).

## Promotion boundary

The deliverable is a runnable **reference Electron substitute architecture**, not a claim of drop-in Electron parity or completion of all 512,820 source prompt/workflow work items. Full promotion remains blocked on the items listed in `../docs/WORKFLOW_APPLICATION_STATUS.md`.

## v0.3.0 audit/upgrade validation — 2026-09-18

- 43 Python unit/integration/regression tests: **PASS** (`LOCAL_TEST_RESULTS_v0.3.0.json`).
- Source v0.2.0 release inventory before modification: **PASS**, 7,342/7,342 hashes matched.
- Embedded DF/Fabric checksum inventories after modification: **PASS** (129 + 141 + 364 + 1,015 + 5,635 checked; zero missing/mismatch).
- Five DF/Fabric trees aggregate-byte comparison against source: **IDENTICAL** (`BASELINE_PRESERVATION_v0.3.0.json`).
- v0.3.0 release-integrity verification: **PASS** (7,353 static files before this summary-line update; final inventory is regenerated at packaging).
- Windows native execution/build qualification: **NOT_RUN**; long-path condition explicitly surfaced by preflight.

## v0.4.0 audit/upgrade validation — 2026-09-18

- 61 Python unit/integration/regression tests: **PASS** (`LOCAL_TEST_RESULTS_v0.4.0.json`).
- Persisted-state semantic validation and referenced-checkpoint verification: **PASS**.
- Strict HTTP JSON duplicate/non-finite rejection and startup release fail-closed regression checks: **PASS**.
- Corrected SHA-256 low-64 witness through locally bound Xtra-Large adapter: **PASS** (`CROSS_TARGET_WITNESS_VALIDATION_v0.4.0.json`). Small/Medium/Large were present but not bound and remain `NOT_RUN` for this probe.
- Local Fabric deterministic diagnostic: **PASS** with deterministic replay (`FABRIC_VALIDATION_v0.4.0.json`), one bound node only.
- Five sealed DF/Fabric trees: **aggregate-byte identical** to the v0.3.0 baseline after transient probe artifacts were restored (`BASELINE_PRESERVATION_v0.4.0.json`).
- Embedded DF/Fabric checksum inventories: **PASS**.
- Windows-native four-tier qualification: **NOT_RUN**.
## v0.5.0 audit/upgrade validation — 2026-09-18

- 72 Python unit/integration/regression tests: **PASS** (`LOCAL_TEST_RESULTS_v0.5.0.json`).
- Reproduced v0.4.0 sealed-tree self-mutation through adapter default `_runs/` output: **CONFIRMED**, then fixed (`RUNTIME_SELF_MUTATION_VALIDATION_v0.5.0.json`).
- Live locally bound Xtra-Large cross-target witness: **PASS** (`CROSS_TARGET_WITNESS_VALIDATION_v0.5.0.json`); Small/Medium/Large remain `NOT_RUN` in this local probe.
- Local Fabric deterministic diagnostic: **PASS**, documented agreement token + deterministic replay (`FABRIC_VALIDATION_v0.5.0.json`).
- Five sealed DF/Fabric trees before/after live cross-target + diagnostic execution: **AGGREGATE-BYTE IDENTICAL** (`BASELINE_PRESERVATION_v0.5.0.json`).
- Strict persisted evidence JSON, clone collision preservation, checkpoint metadata binding, Fabric attestation fail-closed semantics, release metadata strictness, and single-instance locking: **PASS** in regression suite.
- Direct no-`-B` preflight produced zero VEC bytecode-cache directories: **PASS** (`DIRECT_INVOCATION_VALIDATION_v0.5.0.json`).
- Live two-process single-instance probe refused the second shell with exit code 5: **PASS** (`SINGLE_INSTANCE_VALIDATION_v0.5.0.json`).
- Windows-native four-tier qualification: **NOT_RUN**; sealed Xtra-Large relative paths up to 253 characters remain a deployment constraint.

