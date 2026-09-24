"""Command line entry point: ``python -m pk_core <command>``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pk_core.evidence import EvidenceLedger
from pk_core.gate import ConformanceGate
from pk_core.registry import Registry
from pk_core.workflow import WorkflowEngine


def _components(args) -> list:
    registry = Registry(args.package).discover()
    if not len(registry):
        print(f"no components discovered under {args.package!r}", file=sys.stderr)
        raise SystemExit(2)
    if args.element:
        missing = [e for e in args.element if e not in registry]
        if missing:
            print(f"unknown element(s): {', '.join(missing)}", file=sys.stderr)
            raise SystemExit(2)
        return [registry.get(e) for e in args.element]
    return registry.instantiate()


def cmd_list(args) -> int:
    registry = Registry(args.package).discover()
    for element_id in registry.ids():
        component = registry.get(element_id)
        print(f"{element_id}  {component.element_name}")
    print(f"\n{len(registry)} component(s) under {args.package}")
    return 0


def cmd_run(args) -> int:
    ledger = EvidenceLedger(args.evidence)
    engine = WorkflowEngine(ledger)
    results = [engine.run(c) for c in _components(args)]
    for result in results:
        mark = "CERTIFIED" if result.certified else "NOT CERTIFIED"
        print(f"{result.element}  {mark}  coverage={result.coverage:.0%}  {result.name}")
        for stage in result.stages:
            if not stage.ok:
                print(f"    {stage.stage.name} FAILED: {stage.summary}")
                for defect in stage.defects[:10]:
                    print(f"      - {defect}")
    if args.report:
        Path(args.report).write_text(
            json.dumps([r.to_dict() for r in results], indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nreport written to {args.report}")
    return 0 if all(r.certified for r in results) else 1


def cmd_gate(args) -> int:
    ledger = EvidenceLedger(args.evidence)
    engine = WorkflowEngine(ledger)
    results = [engine.run(c) for c in _components(args)]
    gate = ConformanceGate().evaluate(results)
    print(f"verdict: {gate.verdict}  ({len(gate.elements)} elements)")
    for blocker in gate.blockers:
        print(f"  BLOCKER   {blocker}")
    for condition in gate.conditions:
        print(f"  CONDITION {condition}")
    if args.out:
        Path(args.out).write_text(json.dumps(gate.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"gate results written to {args.out}")
    return 0 if gate.verdict != "NO_GO" else 1


def cmd_verify(args) -> int:
    ledger = EvidenceLedger(args.evidence)
    defects = ledger.verify()
    if defects:
        print(f"evidence chain BROKEN ({len(defects)} defects)")
        for defect in defects[:20]:
            print(f"  - {defect}")
        return 1
    print(f"evidence chain intact: {len(ledger)} records, head {ledger.head[:16]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pk_core", description=__doc__)
    parser.add_argument("--package", default="pk_components", help="component package to discover")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="list discovered components")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("run", help="run the W0-W9 workflow")
    p.add_argument("element", nargs="*", help="element ids; default all")
    p.add_argument("--evidence", help="evidence ledger path (JSONL)")
    p.add_argument("--report", help="write a JSON workflow report here")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("gate", help="run the workflow and evaluate the conformance gate")
    p.add_argument("element", nargs="*", help="element ids; default all")
    p.add_argument("--evidence", help="evidence ledger path (JSONL)")
    p.add_argument("--out", help="write PK_GATE_RESULTS.json here")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("verify", help="verify an evidence ledger's hash chain")
    p.add_argument("evidence", help="evidence ledger path (JSONL)")
    p.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
