# VEC1 v0.6.0 Architecture Addendum

## Windows namespace is now an integrity property

v0.6.0 extends the release path profile from length-only risk reporting to Win32 namespace validation. Static release paths are case-folded to detect collisions and each path component is checked for Windows device names, invalid characters, control characters, and trailing dot/space forms. `environment_preflight()` reports schema `VEC1/PREFLIGHT/2` and is not healthy when the static namespace cannot be represented safely on a normal case-insensitive Windows filesystem.

The attached baseline exposed why this matters: two distinct Xtra-Large evidence files differed only by filename case. The guidance record is now stored as `INPUT_PROVENANCE_GUIDANCE.json`; its content hash is preserved while dependent manifests/checksums are regenerated. This is a packaging canonicalization, not a change to VM execution semantics. Because DF_Fabric fail-closes on the SHA-256 of each node container seal, the Fabric `N_XLARGE` pin, its copied manifest record, and Fabric integrity metadata are refreshed to the new Xtra-Large seal rather than bypassing that dependency.

## Isolated renderer launch is fail-safe by default

The shell still discovers Edge/Chrome/Chromium-family executables and starts the renderer in app mode with a dedicated VEC1 user-data directory and extensions disabled. If no isolated compatible executable can be found, v0.6.0 does **not** silently open the tokenized local shell URL in the user's ordinary default-browser profile. The URL is printed for operator diagnosis instead.

An explicit compatibility escape hatch, `--allow-default-browser-fallback`, restores the old OS-default-browser behavior when the operator knowingly accepts that weaker isolation boundary.

## One strict JSON boundary

HTTP mutation bodies and persisted integrity-bearing JSON now converge on `runtime.canonical.strict_json_loads`. The parser rejects duplicate object keys, non-finite constants, invalid UTF-8, excessive raw input (>4,000,000 UTF-8 bytes), parser-recursion overflow, and semantic depth/item/string/canonical-size violations before service mutation logic runs.

This removes a duplicated request parser and makes the same ambiguity/complexity policy apply at both the network and persistence boundaries.

## Strict textual API fields

Names, object identifiers, keyframe object/property identifiers, OCR text, OCR engine metadata, and OCR commit identifiers no longer accept arbitrary JSON values followed by Python string coercion. Values must be strings at the API model boundary and remain subject to explicit size/control-character validation. This prevents values such as `true`, `42`, or arrays from acquiring unintended textual identities.

## Nested evidence reconciliation

The supplied Xtra-Large archive contained nested release manifests that named historical CPython 3.11 cache artifacts no longer present in the delivered tree while delivered CPython 3.13 caches were not represented in those nested manifests. The v0.6.0 canonicalization regenerates those two nested manifests from the actual delivered subtree and refreshes their SHA sidecars. The DF-level payload/manifest/checksum chain is then regenerated outward so the canonicalized node remains self-consistent.

## Boundaries retained

The 0.5 execution-time immutability controls, temporary adapter output routing, child no-bytecode-write policy, strict persisted-state validation, single-instance runtime-state lock, loopback Host/Origin/token boundary, capability checks, and fail-closed Fabric contract remain in place. v0.6.0 does not broaden Electron compatibility or hardware/production qualification claims.
