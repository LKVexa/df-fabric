# VEC1 v0.3.0 Architecture Addendum

## Release plane

v0.3.0 adds a release-integrity plane alongside the renderer, VEC control, VM execution, and Fabric planes. `runtime/release_integrity.py` verifies the exact static package allowlist and SHA-256 digests declared by `PACKAGE_SHA256SUMS.txt`, cross-checks `RELEASE_MANIFEST.json`, and deliberately excludes only mutable runtime state and the two self-referential release metadata files.

The release plane is invoked by `--verify-only` and `--preflight`; normal interactive startup remains fast and does not hash the full package on each launch.

## Windows portability boundary

The DF source trees remain immutable sibling baselines. Because DF_Xtra_Large contains 253-character relative paths, v0.3.0 treats Windows path length as an explicit deployment preflight concern instead of renaming sealed files. This preserves baseline provenance at the cost of requiring a long-path-aware extractor or extremely short package root on classic path configurations.
