# Photon 1.0.1 — integrated into DF_Fabric

* **Host product** — DF_Fabric  
* **Product kind** — DF scheduling/placement fabric (DF0)  
* **Product root** — `<repository root>`  
* **Integration profile** — `VENDORED_UNBOUND`  
* **Integrated (UTC)** — 2026-09-22T16:46:25Z  
* **Release changes** — see `../AUDIT.md`

## What a Photon is, in this installation

The Photon is a **virtual-electron control plane**: a portable identity / state /
clone / evidence layer that can sit on top of a virtual product without owning that
product's execution. It is not a physical-electron simulator, not a QPU, and not the
Chromium/Node.js Electron desktop framework.

Two packages are vendored here, side by side:

| Part | Source | Role |
|---|---|---|
| `control_plane/` | VEC1 Generic Photon **v0.2.0** | headless core: electron identity, canonical state, snapshot/fork/lineage, hash-chained ledger, receipts, security policy, `vecctl` CLI |
| `shell/` | VEC1 Design Photon **v0.6.0** | app shell: loopback-only HTTP service, isolated local renderer, dashboard, release-integrity gate |
| `bridge/` | written for this integration | the one seam between the Photon and the host product |

## Integration profile: VENDORED, UNBOUND

This Photon is installed **unbound on purpose**. No adapter of the host product is
called by it, and no file that was already in this product has been modified,
renamed or moved. Everything the Photon adds lives under `PHOTON/`, plus two
dispatch launchers at the product root.

That means the honest split is:

**Working now, without writing a line of code**

* electron identity, canonical VM-independent state, semantic validation
* snapshot, fork, lineage, restore, diff, equivalence
* append-only hash-chained event ledger with streaming full verification
* execution receipts and evidence records under `control_plane/runtime/evidence/`
* deny-by-default security policy, filesystem confinement, resource quotas
* the dashboard's static surfaces

**Blocked until a bridge is written — fail-closed, by design**

* host attestation: no node reports `bound`
* host build of any native product
* workload execution and cross-node differential comparison
* promotion of any electron to `VERIFIED`
* the shell's Fabric attestation, topology and diagnostic surfaces

Nothing fabricates a pass. `vecctl doctor` will report the missing DF node paths and
an unbound fabric, `vecctl verify` will refuse to promote, and the shell's Fabric
panels will read `BLOCKED`. That is the correct state for an unbound install, and it
is what makes a later `VERIFIED` worth something.

## Start here

```
PHOTON\PHOTON_STATUS.cmd          what this install can and cannot do, and why
PHOTON\PHOTON_CTL.cmd  doctor     full control-plane diagnostic (expect UNBOUND host)
PHOTON\PHOTON_CTL.cmd  create     create an electron; state and ledger work unbound
PHOTON\PHOTON_SHELL.cmd           start the local shell and dashboard
```

POSIX equivalents (`.sh`) sit beside each. `PHOTON.cmd` / `PHOTON.sh` at the product
root dispatch to all of the above. Python 3.10 or newer is required; the launchers
probe `PYTHON`, then `py -3`, `python`, `python3`, and fail with exit 127 rather than
silently picking an unsupported interpreter.

## Binding it

`bridge/BRIDGE_CONTRACT.md` states the exact record shapes. Four functions in
`control_plane/vec1/dfbridge.py` are the whole seam; the control plane, the ledger
and the shell need no changes. The contract also spells out what must *not* be done
to make gates go green.

## Integrity

`PHOTON/SHA256SUMS.txt` covers every file the Photon added. `PHOTON_STATUS` verifies
it. The shell keeps its own release-integrity chain under `shell/` — regenerated for
this location, since the vendored subset is smaller than the original release.

## Closure boundary

The upstream VEC1 package governs 286,440 prompt/workflow pairs and does not claim
them closed; this integration does not close them either, and does not mark any
component checklist `PASS`. See `control_plane/README_FIRST.md` and
`control_plane/AUDIT_REPORT.md` for the upstream statement.
