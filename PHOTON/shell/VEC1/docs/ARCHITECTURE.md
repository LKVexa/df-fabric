# Architecture

## Runtime split

**Renderer plane** — an installed Edge/Chrome app-mode window (default browser fallback) renders `VEC1/ui`. There is no Node.js integration.

**VEC control plane** — `VEC1/app.py` provides loopback JSON RPC. `VECService` owns canonical state, object edits, animation timeline state, OCR observations, clone/checkpoint lifecycle, capability checks, and the append-only event ledger.

**VM execution plane** — `vm_lowering.py` lowers a canonical SHA-256-derived witness into the native source dialect of each bound VM tier. `fabric_bridge.py` invokes the existing `adapter/dfabric/cli.py node-run` surfaces and normalizes target-specific result registers into `result_low64`.

**Fabric plane** — the existing DF_Fabric remains authoritative for node discovery, binding/attestation, deterministic local federation, replica/pipeline/BSP diagnostics, replay, and topology.

## Institute-to-VEC mapping

- DF_Small → minimal/reference VEC work, low-latency state/object/animation operations, MSSL backend.
- DF_Medium → semantic/compiler validation, OCR bridge validation, checkpoints.
- DF_Large → device, I/O, external-interface work only behind explicit capability boundaries.
- DF_Xtra_Large → large-state/long-running/QVM/quorum-oriented reference work.
- DF_Fabric → registry, scheduler, placement, replicas, quorum/differential verification, event history and recovery coordination.

## Security posture

The HTTP service refuses non-loopback binding. Since v0.2.0 it also (1) serves only requests whose `Host` is exactly `127.0.0.1:<port>` or `localhost:<port>` (DNS-rebinding defence), (2) requires `Content-Type: application/json`, a same-origin `Origin` when one is sent, and the per-launch `X-VEC1-Token` on every POST (cross-site request defence; the token is minted with `secrets` at start-up and embedded only in the served renderer page), and (3) opens the renderer in an isolated browser profile with extensions disabled. Checkpoint identifiers are validated as SHA-256 and checkpoint content is re-hashed before restore; all state paths resolve through `SecurityPolicy.safe_path`. VEC1 itself has no outbound network client and no arbitrary host-command endpoint. Filesystem writes are constrained to `VEC1/runtime_state`. OCR/media text is data, never executable instruction. VM source trees are kept as unmodified sibling baselines in the distributed package.

## Why the VM trees are not patched

The supplied DF packages carry their own manifests, SHA-256 inventories, and evidence. Adding VEC files inside those directories would invalidate their baseline inventories. The integration therefore composes them from a sibling control plane and uses their existing adapters rather than mutating sealed source trees.

## v0.3.0 release-integrity plane

`runtime/release_integrity.py` verifies the exact static allowlist and hashes in `PACKAGE_SHA256SUMS.txt`, cross-checks `RELEASE_MANIFEST.json`, and excludes only `VEC1/runtime_state/**` plus the two self-referential release metadata files. `--verify-only` includes this release check; `--preflight` combines it with Python 3.10+ and Windows path-risk reporting.

The embedded DF trees remain immutable. v0.3.0 therefore surfaces the sealed DF_Xtra_Large long-path condition instead of renaming baseline paths and invalidating their provenance.

## v0.4.0 semantic-integrity and fail-closed execution addendum

v0.4.0 validates persisted electron semantics independently of the outer state hash, verifies referenced checkpoints, moves release integrity into the normal startup gate, hardens the JSON parser/capability boundary, and makes Fabric quorum/diagnostic behavior fail closed. The witness normalization value is now the actual SHA-256 low 64 bits. See `docs/ARCHITECTURE_v0.4.0_ADDENDUM.md` for details.

The component registry is now evidence-bounded: a component may be directly implemented, partial, delegated to a sealed DF baseline, or declared-only. Source-corpus enumeration is not treated as proof of runtime implementation.
## v0.5.0 immutable-execution and evidence-integrity addendum

v0.5.0 extends the sealed-baseline boundary from packaging into execution: DF node and Fabric adapter outputs are always routed to temporary paths outside the sealed trees, and child adapter interpreters are prevented from emitting bytecode there. Persisted integrity evidence is parsed with duplicate-key/non-finite rejection; deterministic clone collisions fail without mutation; checkpoint metadata is bound to its referenced snapshot; and Fabric attestation/diagnostics use an explicit fail-closed contract.

Normal shell operation is single-writer for `runtime_state` through an OS advisory lock. Direct `python VEC1/app.py` execution disables bytecode writes before importing VEC runtime modules so the release gate cannot be invalidated by the application itself. See `docs/ARCHITECTURE_v0.5.0_ADDENDUM.md` and `docs/AUDIT_UPGRADE_REPORT_v0.5.0.md`.

