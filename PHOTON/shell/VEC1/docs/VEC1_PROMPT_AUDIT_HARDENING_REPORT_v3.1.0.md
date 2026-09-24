# Audit & Hardening Report — VEC Prompt/Workflow Series v3.0.0 → v3.1.0

## Baseline audited

- Source archive: `VEC1_Prompt_Workflow_Series_Animation_ObjectEdit_OCR_v3.0.0(1).zip`
- Source SHA-256: `14619999eaa6d39cdaefbab41fe5b529f584db832479d58a148b114e2ff42ad1`
- Archive entries: 117
- Prompt/workflow component files: 110
- Parent work items: 24,420
- Nested work items: 488,400
- Total stable work-item IDs/anchors: 512,820
- Duplicate work-item IDs: 0
- Duplicate anchors: 0
- Source checksum inventory mismatches: 0
- ZIP CRC test: PASS

## Findings and applied fixes

| ID | Severity | Finding | Applied v3.1.0 hardening |
|---|---|---|---|
| A-01 | High | No explicit rule treated OCR/media/document/archive content as untrusted data rather than instructions. | Added authority hierarchy, prompt-injection/data boundary, and archive/media import safety rules. |
| A-02 | High | No normative work/check status taxonomy; unexecuted verification could be ambiguously summarized. | Added `PASS/FAIL/BLOCKED/NOT_APPLICABLE` work states and `PASS/FAIL/NOT_RUN/NOT_APPLICABLE` check states. |
| A-03 | High | Mutation prompts lacked a mandatory baseline→candidate→verify→promote sequence. | Added baseline hashing, candidate isolation, diff basis, verification, and promotion gate. |
| A-04 | Medium-High | Parent workflows always said “implement,” even when the source task is design/documentation/verification only. | Added execution-mode classification and minimum-complete-action rule. |
| A-05 | Medium-High | “As applicable” gates did not require evidence of applicability decisions. | Applicability decisions/rationale are now mandatory and machine-recorded. |
| A-06 | Medium | Independent-review language could be self-certified by an executor. | Added explicit review-independence rule; required unavailable review yields `BLOCKED`. |
| A-07 | Medium | No run-ledger/idempotency/resume contract for a 512,820-item corpus. | Added run-ledger schema, idempotency-key recommendation, checkpoint/resume and baseline-drift checks. |
| A-08 | Medium | No machine-readable per-item result contract. | Added `VEC/WORK_ITEM_RESULT/3.1.0` JSON Schema plus evidence/run-ledger schemas. |
| A-09 | Medium | Evidence reuse/no-op behavior was unspecified. | Added evidence hash compatibility and `NO_OP` execution mode rules. |
| A-10 | Medium | Archive/media parsers lacked explicit traversal/bomb/nesting/resource protections. | Added bounded decode/extraction rules and path/symlink/device-path defenses. |
| A-11 | Medium | Multimedia rules existed in prompts but were not centralized as normative invariants. | Centralized OCR observation provenance, atomic object edits, deterministic animation/timebase rules. |
| A-12 | Low | Source requirement and execution instructions were concatenated in one prose sentence without an explicit authority delimiter. | Individual prompts now explicitly invoke the hardened contract; file-level authority hierarchy separates source scope from untrusted content. |

## Compatibility decision

This is a **minor version bump** to `3.1.0`: all 512,820 work-item IDs, anchors, source requirements, component file names, manifest rows, and component paths remain stable. The execution contract and workflows are stricter, but the catalog identity is preserved.

## Promotion rule

v3.1.0 supersedes v3.0.0 for new executions. Existing v3.0.0 evidence is not automatically invalid, but it must be labeled with the older contract version and must not be represented as v3.1.0 evidence without revalidation against the hardened gates.
