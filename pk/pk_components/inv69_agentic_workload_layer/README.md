# INV-69 - Agentic workload layer

**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The agentic workload layer runs model-driven agents that plan and call tools. What makes that safe to operate is containment at the plan level: each agent has an allowlist of tools, a step budget, and any tool with side effects waits for a recorded approval before it runs. Every step lands in a transcript, so what an agent did is always reconstructable.

## Responsibility

Own agent execution governance: tool allowlists, step budgets, approval gates on side-effectful tools, sandbox routing and a complete step transcript.

## Owns

- Per-agent tool allowlists
- Step and cost budgets
- Approval gates for side-effectful tools
- Routing tool execution to a sandbox tier
- The step transcript

## Explicitly does not own

- The model itself
- Tool implementations
- Sandbox internals
- Identity issuance
- Business approval workflows

## Non-goals

- Running the model
- Implementing tools
- Building sandboxes

## Interfaces

- `approval` - PK_AGENT_APPROVAL/1 - a recorded human or policy approval
- `step` - PK_AGENT_STEP/1 - one tool call and its outcome
- `transcript` - PK_AGENT_TRANSCRIPT/1 - ordered steps

## Service-level objectives

- **containment** - zero calls to tools outside the allowlist (error budget: no budget)
- **approval** - zero side-effectful calls without an approval record (error budget: no budget)
- **transcript completeness** - every step recorded (error budget: no budget)

## Running it

```
python -m pk_core list
python -m pk_core run INV-69 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-69 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-69`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-69`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
