# Photon host-bridge contract

The Photon control plane is host-neutral. Everything it needs from the product it
is vendored into passes through one module:

    PHOTON/control_plane/vec1/dfbridge.py

In this installation that module is the **UNBOUND** profile: it answers every host
question with a structured `UNBOUND` record and binds nothing. The control plane,
the ledger, the electron store, snapshot/fork/lineage, receipts and the CLI are all
fully functional; only host execution is absent, and every gate that depends on host
execution fails closed by design.

Binding the Photon to its host product means replacing four functions. Nothing else
in `control_plane/` or `shell/` needs to change.

---

## 1. `find_make() -> str | None`

Already host-neutral. Returns the path to a GNU-compatible `make`, honouring
`DF_MAKE` / `PHOTON_MAKE` first. Leave as shipped unless the host product needs a
different builder.

## 2. `build_required() -> dict`

Build whatever native products the host needs before it can execute.

```jsonc
{
  "make": "<path or null>",
  "nodes": {                      // one entry per execution node you define
    "<NODE_ID>": { "returncode": 0, "stdout": "...", "stderr": "...", "note": "..." }
  },
  "ok": true,                     // true only if every required node built
  "blocked": "<reason>"           // present only when the build could not start
}
```

## 3. `attest(out_path=None) -> (runrec, data)`

Report which execution nodes are present and usable. `data` must carry a `nodes`
object; a node counts as bound only when its value is an object with `"bound": true`.

```jsonc
// data
{
  "schema": "PHOTON/HOST_BRIDGE/1",
  "nodes": {
    "<NODE_ID>": { "bound": true, "path": "...", "kind": "...", "version": "..." }
  }
}
// runrec
{ "argv": [...], "returncode": 0, "stdout": "...", "stderr": "..." }
```

`attest` must write `data` to `out_path` as JSON when `out_path` is given, and must
never leave a stale file from an earlier run in place.

## 4. `fabric_run(program, out_path, event_log_path=None, profile=..., placement=..., strict=True, programs=None) -> (runrec, data)`

Execute the sealed workload across the host's nodes and return a comparison verdict.

```jsonc
// data
{
  "verdict": "CROSS_NODE_DIFFERENTIAL_AGREEMENT",   // the only accepted value
  "nodes":  { "<NODE_ID>": { "bound": true, "result": { ... } } },
  "replay": { "ok": true }
}
```

Promotion to `VERIFIED` requires all of:

* `data.verdict == "CROSS_NODE_DIFFERENTIAL_AGREEMENT"`;
* every node named in `config/vec1.json → required_nodes` present and bound;
* the event-log replay self-check passing;
* no schema, integrity or policy failure anywhere in the chain.

Anything else marks the instance `FAULTED` or `BLOCKED`. Do not soften this: the
value of the control plane is that its `VERIFIED` means something.

---

## Node set

`control_plane/config/vec1.json` carries `strict_four_node_execution` and the
accepted verdict. When you bind a host with a node set other than the DF four
(`N_SMALL`, `N_MEDIUM`, `N_LARGE`, `N_XLARGE`), set `strict_four_node_execution`
to `false` and enforce your own required set inside `attest` / `fabric_run`, or
edit `REQUIRED_NODES` in `control_plane/vec1/core.py` to match.

## Shell

`shell/VEC1/runtime/fabric_bridge.py` and `shell/VEC1/runtime/vm_lowering.py` look
for `DF_Fabric` and `DF_*` node directories beside the shell package root. They are
absent here, so the shell degrades to `BLOCKED` on attestation, topology and
diagnostic surfaces, and serves the rest of the dashboard normally. Bind the shell
by pointing those two modules at the host product's own adapters.

## What must not be done to make things pass

Do not stub a `bound: true` node, do not hand back
`CROSS_NODE_DIFFERENTIAL_AGREEMENT` from a bridge that ran nothing, and do not mark
component checklists `PASS` without the evidence behind them. The vendored package
carries its own closure boundary (`control_plane/README_FIRST.md`), and this
integration does not close it.
