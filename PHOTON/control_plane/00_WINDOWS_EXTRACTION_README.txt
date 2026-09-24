VEC1 Generic Photon v0.2.0 WindowsSafe-r1 — Windows-safe path canonicalization

This repack fixes the archive-level Windows path failures without renaming the core Bottle Rocket VM package directory.

RESULT
- Original maximum relative path: 267 characters
- Rebuilt maximum relative path: 156 characters
- Relative paths over 180 characters: 0
- Windows case-insensitive filename collisions: 0
- Invalid/reserved Windows path components: 0
- Classic Win32 package-root budget: 102 characters (259 - separator - 156)
- Recommended extraction root: 90 characters or fewer for additional shell/tooling margin

WHAT CHANGED
- Removed redundant adjacent duplicate directory segments in the workflow input tree.
- Compacted long qualification/evidence directory names with deterministic aliases.
- Compacted filenames over 56 characters with an 8-hex SHA-1-derived suffix to prevent collisions.
- Preserved the long core Bottle Rocket VM package identity directory.
- Removed the unnecessary outer VEC1_ES_0.2.0 archive folder so the extracted package starts at its actual project root.
- Resolved the INPUT_PROVENANCE.json/input_provenance.json Windows collision by preserving the lowercase record as INPUT_PROVENANCE_GUIDANCE.json.

Use WINDOWS_PATH_PREFLIGHT.cmd after extraction to confirm the full-path budget at the actual destination. Long-path-enabled Windows remains supported, but it is no longer required for the archive's relative paths when the package root stays within the budget above.
