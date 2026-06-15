from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping

from semantic_control_kernel.orchestrator_contract_background import _continue_after_interaction
from semantic_control_kernel.orchestrator_contract_legacy import _legacy_request_shell


def _json_from_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("STDIN JSON root must be an object.")
    return payload


def _stdout(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(dict(payload), ensure_ascii=True))
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if any(token in {"--request", "--response"} for token in args):
        return _legacy_request_shell(args)
    parsed = _parse_subcommand(args)
    if parsed.command == "continue-after-interaction":
        invalid_id = _invalid_state_id_error("workflow_run_id", parsed.workflow_run_id)
        if invalid_id is not None:
            _stdout(
                {
                    "schema_version": "kernel.background_continuation_result.v1",
                    "status": "error",
                    "workflow_run_id": parsed.workflow_run_id,
                    "workflow_tool": parsed.workflow_tool,
                    "error": invalid_id,
                }
            )
            return 2
        _stdout(_continue_after_interaction(parsed.workflow_run_id, parsed.workflow_tool))
        return 0
    _dispatch_mcp_command(parsed)
    return 0


def _parse_subcommand(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="semantic_control_kernel.orchestrator_contract")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list-mcp-tools")
    list_parser.add_argument("--scope", default="all", choices=("permanent_agent", "event_scoped_recovery", "kernel_internal", "all"))
    for name in (
        "mcp-call",
        "healthcheck",
        "list-client-events",
        "submit-interaction-response",
        "cancel-interaction",
        "list-event-scoped-tools",
    ):
        subparsers.add_parser(name)
    continue_parser = subparsers.add_parser("continue-after-interaction")
    continue_parser.add_argument("--workflow-run-id", required=True)
    continue_parser.add_argument("--workflow-tool", required=True)
    return parser.parse_args(args)


def _invalid_state_id_error(field_name: str, value: str) -> dict[str, str] | None:
    from semantic_control_kernel.repository.ids import require_state_id

    try:
        require_state_id(field_name, value)
    except ValueError as exc:
        return {"code": "invalid_state_id", "message": str(exc)}
    return None


def _dispatch_mcp_command(parsed: argparse.Namespace) -> None:
    from semantic_control_kernel import mcp_contract

    if parsed.command == "list-mcp-tools":
        _stdout(mcp_contract.list_mcp_tool_definitions(parsed.scope))
    elif parsed.command == "mcp-call":
        _stdout(mcp_contract.call_mcp_tool(_json_from_stdin()))
    elif parsed.command == "healthcheck":
        _stdout(mcp_contract.kernel_healthcheck())
    elif parsed.command == "list-client-events":
        _stdout(mcp_contract.list_client_frontend_events(_json_from_stdin()))
    elif parsed.command == "submit-interaction-response":
        _stdout(mcp_contract.submit_user_interaction_response(_json_from_stdin()))
    elif parsed.command == "cancel-interaction":
        _stdout(mcp_contract.cancel_user_interaction(_json_from_stdin()))
    elif parsed.command == "list-event-scoped-tools":
        _stdout(mcp_contract.list_event_scoped_tool_definitions(_json_from_stdin()))
    else:
        raise AssertionError(f"Unhandled command: {parsed.command}")
