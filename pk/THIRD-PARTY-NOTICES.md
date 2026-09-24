# Third-party notices

The components under `pk_components/` and the runtime under `pk_core/` were
authored for this estate from the **Post-Kubernetes Master Prompt & Workflow
Series v4.0.0**, supplied by the owner. Each element this project OWNS carries
that series' per-element `MASTER.md` verbatim under
`pk_components/<element>/MASTER.md`, and its 100 requirements verbatim in
`CHECKLIST.json`. Elements installed here only as integration dependencies
carry their code and checklist; their master prompts live with the project that
owns them (see `PK_OWNERSHIP.json` and `PK_ROUTING.json`).

No third-party source code was copied into this payload. `pk_core` and every
component implementation depend on the Python standard library only; the
optional `tests/` suite uses pytest, and `SELFTEST.py` runs the same checks with
no dependencies at all.

The owner-authored material in this distribution is released by RUSSELL PHILIP SMITHSON under Apache-2.0; see `../LICENSE` and `../NOTICE`.
