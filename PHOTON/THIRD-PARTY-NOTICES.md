# Third-party notices — Photon 1.0.0 in DF_Fabric

Recorded at integration time, 2026-09-22T16:46:25Z.

| Part | Origin | Licence / notice | Disposition |
|---|---|---|---|
| `control_plane/` | VEC1 Electron Substitute (Generic Photon) v0.2.0 | Package `THIRD-PARTY-NOTICES.md` states no donor code was copied in; `vec1/`, `tests/`, `ui/`, CI written new for that candidate. No separate LICENSE file shipped at package root. | vendored unmodified except `vec1/dfbridge.py` (replaced with the unbound profile) and `config/vec1.json` (node assumptions relaxed) |
| `shell/` | VEC1 Electron Substitute (Design Photon) v0.6.0 | `VEC1/THIRD-PARTY-NOTICES.md` states the overhaul pulled no third-party source; Python standard library is the only runtime dependency. | vendored unmodified; release-integrity chain regenerated for the smaller file set |
| `bridge/`, `PHOTON_STATUS.py`, launchers | written for this integration | same terms as the host product | new |
| DF_Small, DF_Medium, DF_Large, DF_Xtra_Large, DF_Fabric | bundled in both source packages | `All rights reserved. (c) Russell Philip Smithson.` — the packages note this is not a grant of rights | **not vendored** |

Release 1.0.1 licensing update: the owner-authored material in this distribution
is released by RUSSELL PHILIP SMITHSON under Apache-2.0; see `../LICENSE` and
`../NOTICE`. The table above records the historical source-package notices.
The control-plane integrity checks and receipt validation were changed in this release.
