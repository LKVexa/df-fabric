# Audit and release 1.0.1

Source: the supplied DF_Fabric folder. Original files were left unchanged;
this distribution was repaired in a separate working copy.

## Fixes

- Replaced permissive integrity paths with canonical relative-path checks.
  Traversal, absolute paths, Windows stream/alias syntax, duplicate entries,
  invalid digests, empty evidence and filesystem links/reparse points fail closed.
  Manifest sizes/counts require integers; payload byte counts are verified.
- Rebuilt the stale 129-file root inventory to cover the full Photon/PK bundle.
  Added an auxiliary inventory covering both native root metadata files, while
  excluding Git metadata and mutable runtime/build outputs from static claims.
- Enforced strict four-node receipt checks independently of configuration
  relaxation; enforced configured strictness even for a non-strict call.
  VENDORED_UNBOUND cannot mark an execution VERIFIED, even with a synthetic
  complete-node result. Replay success must be the boolean true.
- Restored the missing Photon VERIFY_PACKAGE module and made Photon status use
  strict checksums. Removed workstation-specific path defaults. POSIX Photon
  dispatchers invoke shell scripts explicitly, including from unpacked Windows
  archives without executable mode bits.
- Added README, Apache-2.0 LICENSE/NOTICE naming RUSSELL PHILIP SMITHSON,
  security guidance, release version 1.0.1 and pinned Windows/Linux CI.
- Clean-runner testing exposed undeclared NumPy imports in the pinned fabric
  core. REQUIREMENTS.txt is now pip-installable with Python-specific version
  pins: 2.2.6 for Python 3.10, 2.4.6 for Python 3.11, and 2.5.3 for 3.12+.
  Versions and Python requirements were checked against official PyPI metadata:
  [2.2.6](https://pypi.org/project/numpy/2.2.6/),
  [2.4.6](https://pypi.org/project/numpy/2.4.6/),
  [2.5.3](https://pypi.org/project/numpy/2.5.3/).

## Validation

Local Python 3.12: 12 adapter/Photon integrity regressions (11 passed, one
filesystem-link creation test skipped because the Windows account lacks that
privilege); 33 control-plane tests (32 passed, one native four-node integration
test skipped); 80 shell tests passed; 952 PK self-checks passed. Baseline
control-plane testing reproduced the one-node strictness failure before repair.

Available fabric battery: six gates passed and two were skipped because the
four sibling VM containers were absent. Core selfcheck, pinned pacore digest,
schema/citation checks and full static inventories passed. The untouched pacore
tree digest remains `f9d0991b6175e3bd7b33c4915f69078c36cd67c22bd7dad8d97370334251388c`.

JSON, Python and JavaScript syntax checks and targeted token/private-key scans
are part of preparation. CI runs these portable suites on Windows and Linux
with Python 3.10, 3.11 and 3.14. Consult the actual workflow result for each platform.

These checks validate this local reference distribution. They do not certify
native VM behavior, four-node execution, cross-host networking or hardware
isolation. Historical conformance reports and component version labels are
retained as provenance, not represented as new release evidence. Node-registry
pins still identify original node distributions and require review before
using independently upgraded siblings. Hash checks assume a stable local tree
and do not establish independent publisher identity.
