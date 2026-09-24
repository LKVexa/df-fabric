# DF_Fabric adapter portability patch applied by VEC1 ES v0.1.0

Only the integrated `DF_Fabric/adapter/dfabric` copy is changed. The four VM node containers remain byte-for-byte source-package copies (apart from machine-specific build artifacts created during local use, which their manifests already exclude).

The fabric-side patch adds host-portability resolution only:

- resolve native node tools with `.exe` suffix on Windows;
- accept `DF_MAKE`, `make`, `mingw32-make`, or `gmake`;
- detect OpenSSL headers from common environment roots or a compiler preprocessor probe.

No VM ISA, PA-LCTL semantics, lowering rules, fabric scheduling semantics, trust boundary, or claim ceiling is changed. The original input ZIP hashes are recorded in `evidence/INPUT_HASHES.json`. The modified DF_Fabric container is resealed by regenerating its own `MANIFEST.json` and `SHA256SUMS.txt`.
