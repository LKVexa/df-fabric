# Institute-Guided Assembly Notes

## Purpose

The supplied **DF VM Technical Institute v2.1.2** is used as the explanatory authority for how the four VM tiers and `DF_Fabric` are composed. The VEC1 layer does not reinterpret the suite as one monolithic VM; it preserves the Institute's tiered-node/federation model and places an Electron-style application control plane above it.

## Assembly model applied

| VEC1 role | DF substrate | Integration behavior |
|---|---|---|
| Lightweight/reference execution | `DF_Small` | MSSL witness lowering; preferred for low-latency interactive/object/animation state work. |
| Semantic/compiler qualification | `DF_Medium` | LCTLC/1.1 witness lowering; preferred for semantic validation, OCR bridge validation, and checkpoint-oriented work. |
| Device/service boundary | `DF_Large` | LCTLC/1.2 witness lowering; reserved for service, device, file, and explicit external-interface work behind capability checks. |
| Large-state/QVM reference | `DF_Xtra_Large` | LCTLC/1.0/QVM witness lowering; preferred for long-running, large-state, quorum/reference operations. |
| Federation | `DF_Fabric` | Existing discovery, binding, attestation, deterministic local federation, replay, replica/pipeline/BSP diagnostics, and topology remain authoritative. |

## Composition rule

The supplied DF package trees remain byte-preserved baselines. VEC1 is added as a sibling control/runtime layer and invokes each package through its existing `adapter/dfabric/cli.py` surface. This prevents the integration itself from invalidating the source packages' manifests or SHA-256 inventories.

The reference execution path is:

1. A renderer request arrives at the loopback-only VEC1 service.
2. VEC1 validates capability, state precondition, and canonical JSON input.
3. The requested state operation is applied atomically to the VEC model and appended to the hash-chained event ledger.
4. The scheduler maps the workload class to the best currently bound VM tier, with an explicit degraded fallback if a preferred tier is unavailable.
5. For cross-target verification, VEC1 derives one canonical witness from the state payload, lowers it to the native source dialect of every bound tier, runs it through that tier's existing adapter, and normalizes the tier-specific result register to `result_low64`.
6. `DF_Fabric` remains the source of truth for node presence/binding and deterministic federation diagnostics.

## Renderer boundary

The current reference implementation intentionally does not embed or redistribute Chromium. It uses an installed Edge/Chrome app-mode window when available, or the system browser as fallback. This removes Electron's bundled Node/main-process requirement while keeping web rendering outside the DF VM claim boundary.

## Evidence boundary

The isolated validation copy built all four VM tiers successfully and the same canonical witness executed successfully through all four native adapters. That proves the adapter/lowering/normalization path used by this reference implementation. It does **not** prove full semantic lowering of every VEC object-edit, animation, OCR, media, or Electron-compatible API operation into each VM ISA.
