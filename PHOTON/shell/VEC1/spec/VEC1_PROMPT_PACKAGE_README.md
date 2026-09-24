# VEC-1 Prompt & Workflow Series — Animation + Object Editing + OCR v3.1.0

This hardened release preserves the complete v3.0.0 work-item catalog while strengthening execution safety, determinism, provenance, evidence, resumability, and promotion semantics.

## Coverage preserved

- Components: **110**
- Parent work items: **24,420**
- Nested work items: **488,400**
- Total prompt/workflow work items: **512,820**
- Stable work-item IDs/anchors preserved: **512,820**

## New normative controls

- `MASTER_EXECUTION_CONTRACT_v3.1.0.md`
- baseline → candidate → diff → verify → promote discipline
- explicit execution-mode and applicability classification
- truthful `PASS/FAIL/BLOCKED/NOT_APPLICABLE` work status
- truthful `PASS/FAIL/NOT_RUN/NOT_APPLICABLE` check status
- untrusted OCR/media/document/archive content boundary
- independent-review non-self-certification
- run-ledger/idempotency/resume rules
- OCR provenance, atomic object editing, deterministic animation rules
- bounded parser/archive/decode resource protections
- machine-readable result/evidence/run-ledger schemas

## Key files

- `AUDIT_HARDENING_REPORT_v3.1.0.md` — baseline findings and applied repairs.
- `MASTER_EXECUTION_CONTRACT_v3.1.0.md` — normative execution contract.
- `prompt_workflows/` — hardened component prompt/workflow series.
- `schemas/work_item_result.schema.json`
- `schemas/evidence_record.schema.json`
- `schemas/run_ledger.schema.json`
- `PROMPT_WORKFLOW_MANIFEST.csv` / `.jsonl` — unchanged stable work-item catalog.
- `COMPONENT_MANIFEST.json` — updated version and component hashes.
- `VALIDATION_REPORT.md` — structural and hardening validation.
- `SHA256SUMS.txt` — hashes for the hardened release.
