from __future__ import annotations

ALLOWED_ACTIONS: tuple[str, ...] = ()


def main(argv: list[str] | None = None) -> int:
    from semantic_control_kernel.orchestrator_contract_cli import main as _cli_main

    return _cli_main(argv)


def _background_failure_summary(exc):
    from semantic_control_kernel.orchestrator_contract_background import _background_failure_summary as _impl

    return _impl(exc)


def _continue_after_interaction(workflow_run_id: str, workflow_tool: str):
    from semantic_control_kernel.orchestrator_contract_background import _continue_after_interaction as _impl

    return _impl(workflow_run_id, workflow_tool)


def _legacy_request_shell(argv: list[str]) -> int:
    from semantic_control_kernel.orchestrator_contract_legacy import _legacy_request_shell as _impl

    return _impl(argv)


def _split_agent_payload(payload):
    from semantic_control_kernel.orchestrator_contract_legacy import _split_agent_payload as _impl

    return _impl(payload)


__all__ = [
    "ALLOWED_ACTIONS",
    "_background_failure_summary",
    "_continue_after_interaction",
    "_legacy_request_shell",
    "_split_agent_payload",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
