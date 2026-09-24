# DF Fabric

Version **1.0.1** (`DF-PA21.2-1.0.1`) — by **RUSSELL PHILIP SMITHSON**.

DF Fabric provides PA-LCTL federation adapters, deterministic witnesses and
conformance checks for four local VM node types. It also includes the Photon
control plane and loopback UI shell, plus the PK component contracts and runtime.

This repository contains the `DF_Fabric` source folder as its own distribution.
It contains no embedded VM. Photon is delivered in `VENDORED_UNBOUND` mode:
lifecycle and evidence features work locally; host execution remains blocked.
The fabric models federation using local processes. Cross-host federation and
physical QPU execution are not implemented or certified by this release.

## Run local checks

Python **3.10 or later** is required; runtime and default checks use the standard
library. From the repository root:

```sh
python -B tools/validate_release.py
python -B adapter/dfabric/cli.py fabric-verify
python -B PHOTON/PHOTON_STATUS.py --json
```

The first command verifies release hashes and runs the adapter regressions,
Photon control-plane tests, Photon shell tests and dependency-free PK checks.
The second runs available fabric gates and lists missing-node checks as SKIPPED.
A PASS with skips does not demonstrate four-node execution.

For the local Photon UI, run `PHOTON.cmd` on Windows or `sh PHOTON.sh` on POSIX.
The shell binds only to 127.0.0.1 and guards mutations with a launch token.

## Native federation prerequisites

The separate `DF_Small`, `DF_Medium`, `DF_Large`, and `DF_Xtra_Large` distributions
must be placed beside this repository using those directory names, or supplied
through `--nodes-root`. Native compilation requires their documented C11/make/
OpenSSL and Java toolchains. `BUILD` writes build artifacts into those node trees.
Registry pins still identify the historical node distributions: independently
upgraded nodes need deliberate pin review and a fresh four-node integration run.

See [the assembly guide](README_START_HERE.md) for architecture and commands,
[AUDIT.md](AUDIT.md) for changes and validation limits, and
[SECURITY.md](SECURITY.md) for the trust boundaries.

## Integrity and licensing

`MANIFEST.json` inventories the full static distribution, including Photon and PK.
`SHA256SUMS.txt` binds that inventory and static files. `FILES.sha256` additionally
binds both root metadata files. Mutable runtime/build outputs and Git metadata are
excluded. Hashes detect drift; they are not an independent authenticity signature.
The pinned `core/reference/pacore` bytes are unchanged.

Copyright 2026 **RUSSELL PHILIP SMITHSON**. Licensed under
[Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
