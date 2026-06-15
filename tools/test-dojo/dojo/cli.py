from __future__ import annotations

import argparse
import json
import sys

from .inventory import validate_inventory_gate, write_inventory_report
from .manifest import discover_suites, select_suites, validate_suite
from .paths import resolve_paths
from .reports import CaseResult, SuiteResult, utc_now, write_index
from .sandbox import create_sandbox


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vision Pipeline Test Dojo skeleton.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List discovered Dojo suites.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect and validate suite manifests.")
    inspect_parser.add_argument("--suite", required=True, help="Suite name or 'all'.")
    inspect_parser.add_argument("--json", action="store_true", help="Emit JSON.")

    run_parser = subparsers.add_parser("run", help="Create a skeleton dry-run report for suites.")
    run_parser.add_argument("--suite", required=True, help="Suite name or 'all'.")
    run_parser.add_argument("--mode", default="deterministic", choices=["deterministic", "live-canary", "inventory-only", "smoke"])
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument("--execute", action="store_true", help="Attempt real driver execution. Not implemented in the skeleton.")

    args = parser.parse_args(argv)
    paths = resolve_paths()
    suites = discover_suites(paths.suite_dir)

    if args.command == "list":
        for suite in suites:
            print(f"{suite.name}\t{suite.kind}\t{suite.driver}\t{suite.display_name}")
        return 0

    if args.command == "inspect":
        selected = select_suites(suites, args.suite)
        payload = _inspect_payload(selected)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            _print_inspection(payload)
        return 1 if payload["errors"] else 0

    if args.command == "run":
        if args.execute:
            print("Real driver execution is not implemented in the skeleton yet.", file=sys.stderr)
            return 3
        selected = select_suites(suites, args.suite)
        inspection = _inspect_payload(selected)
        if inspection["errors"]:
            _print_inspection(inspection)
            return 2
        sandbox = create_sandbox(paths.run_root, paths.report_root, args.run_id)
        write_inventory_report(sandbox.report_dir / "inventory.json", selected)
        started_at = utc_now()
        suite_results = [
            SuiteResult(
                name=suite.name,
                display_name=suite.display_name,
                status="planned",
                cases=tuple(
                    CaseResult(
                        id=case.id,
                        title=case.title,
                        status="planned",
                        message="Skeleton dry-run only; driver execution pending.",
                        driver=suite.driver,
                    )
                    for case in suite.cases
                ),
            )
            for suite in selected
        ]
        index_path = write_index(
            sandbox.report_dir,
            run_id=sandbox.run_id,
            mode=args.mode,
            status="planned",
            suites=suite_results,
            started_at=started_at,
        )
        print(f"[DOJO] skeleton report: {index_path}")
        return 0

    return 5


def _inspect_payload(suites) -> dict:
    suite_payloads: list[dict] = []
    errors: list[str] = []
    for suite in suites:
        suite_errors = validate_suite(suite)
        suite_errors.extend(validate_inventory_gate(suite))
        errors.extend(f"{suite.name}: {error}" for error in suite_errors)
        suite_payloads.append(
            {
                "name": suite.name,
                "display_name": suite.display_name,
                "module": suite.module,
                "kind": suite.kind,
                "driver": suite.driver,
                "inventory_gate": suite.inventory_gate,
                "modes": list(suite.modes),
                "case_count": len(suite.cases),
                "cases": [
                    {
                        "id": case.id,
                        "title": case.title,
                        "type": case.type,
                        "risk": case.risk,
                        "expected_actions": list(case.expected_actions),
                    }
                    for case in suite.cases
                ],
                "errors": suite_errors,
            }
        )
    return {"schema_version": 1, "suite_count": len(suites), "suites": suite_payloads, "errors": errors}


def _print_inspection(payload: dict) -> None:
    for suite in payload["suites"]:
        status = "OK" if not suite["errors"] else "ERROR"
        print(f"[{status}] {suite['name']} ({suite['driver']}) - {suite['case_count']} cases")
        for error in suite["errors"]:
            print(f"  - {error}")
    if payload["errors"]:
        print("[DOJO] inspection failed")
    else:
        print("[DOJO] inspection passed")
