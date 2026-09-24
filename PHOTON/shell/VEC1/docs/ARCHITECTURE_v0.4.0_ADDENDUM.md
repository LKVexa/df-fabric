# VEC1 v0.4.0 Architecture Addendum

## Integrity becomes a startup gate

v0.4.0 moves static release verification from an optional verification path into normal startup. The service refuses to bind its loopback listener when the static allowlist, file digests, manifest contract, version, or release references fail validation. `--version` remains metadata-only; `--preflight` and `--verify-only` retain their explicit verification roles.

The in-package checksum inventory detects accidental corruption and inconsistent packaging. It is **not an authenticity signature**: an attacker able to replace the package and coherently rewrite both manifest and checksum inventory is outside this trust root. The external ZIP SHA-256 (and, for production use, a separately managed signature) is the transport/authenticity boundary.

## Persisted-state boundary

Electron JSON is no longer trusted merely because its outer `state_hash` matches. `runtime/model.py::validate_state` validates identity, lineage, lifecycle state, bounds, object hashes, animation references, OCR provenance fields, checkpoint references, counters, finite-number rules, and the outer hash before state can participate in execution. This preserves editable JSON while making edits subject to the same schema invariants as runtime-generated state.

Referenced checkpoint files are now part of the full integrity sweep. Orphan checkpoint files are reported but do not fail the gate because a crash can leave a fully written snapshot before its state reference is committed.

## Fabric boundary

The four contract node names are fixed: `N_SMALL`, `N_MEDIUM`, `N_LARGE`, and `N_XLARGE`. Unknown attestation records are diagnostic metadata and never count toward `require_all`. Cross-target verification is blocked if attestation itself fails, and a Fabric diagnostic process failure cannot inherit a passing verdict from malformed output.

The canonical witness is now the actual low 64 bits (last 16 hexadecimal digits) of the SHA-256 digest. This fixes the prior 32-bit value that had been labeled `witness_low64`.

## Capability and HTTP boundary

An explicitly empty capability set now means deny-all. Capability manifests include a canonical capability hash. Direct Fabric diagnostics and HTTP shutdown pass through capability checks.

The JSON request boundary rejects duplicate keys, NaN, Infinity, -Infinity, non-object bodies, chunked transfer, oversized bodies, and short bodies. Existing Host/Origin/session-token controls remain in place.

## Ledger/status boundary

Full ledger verification is streaming. Dashboard status uses cached ledger health and re-verifies after an observed file fingerprint change rather than replaying the entire ledger on every refresh. Full `--verify-only` still traverses the chain.

## Evidence-bounded component registry

The 110-component registry now uses four maturity states: `REFERENCE_IMPLEMENTED`, `PARTIAL`, `DELEGATED_TO_DF`, and `DECLARED_ONLY`. This is a claim-boundary correction: source-corpus presence is not treated as executable implementation evidence.
