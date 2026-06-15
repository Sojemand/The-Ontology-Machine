from __future__ import annotations

import re
from pathlib import Path

from .command_matrix import CommandSpec
from .paths import ACTIVE_SCAN_ROOTS, FORBIDDEN_PATTERN, GENERATED_DIR_NAMES, PIPELINE_ROOT


def _scan_forbidden_matches() -> list[dict[str, str]]:
    matcher = re.compile(FORBIDDEN_PATTERN)
    matches: list[dict[str, str]] = []
    for relative in ACTIVE_SCAN_ROOTS:
        path = PIPELINE_ROOT / relative
        if path.is_dir():
            for candidate in sorted(p for p in path.rglob("*") if _should_scan_file(p)):
                matches.extend(_file_matches(candidate, matcher))
        elif _should_scan_file(path):
            matches.extend(_file_matches(path, matcher))
    return matches


def _file_matches(path: Path, matcher: re.Pattern[str]) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: list[dict[str, str]] = []
    for match in matcher.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        snippet = text.splitlines()[line - 1].strip()
        found.append(
            {
                "path": path.relative_to(PIPELINE_ROOT).as_posix(),
                "matched_pattern": match.group(0),
                "line": str(line),
                "snippet": snippet,
            }
        )
    return found


def _should_scan_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() != ".pyc" and not any(part in GENERATED_DIR_NAMES for part in path.parts)


def _execute_scan_command(spec: CommandSpec) -> tuple[int, str, str]:
    if spec.purpose == "legacy_patterns":
        matches = _scan_forbidden_matches()
        if not matches:
            return 0, "No forbidden old-Kernel patterns found in active roots.\n", ""
        stdout = "\n".join(f"{match['path']}:{match['line']}:{match['matched_pattern']}" for match in matches) + "\n"
        return 1, stdout, ""
    if spec.purpose == "recovery_leakage":
        disallowed, allowed = _scan_recovery_tool_matches()
        if disallowed:
            stdout = "\n".join(f"{match['path']}:{match['line']}:{match['matched_pattern']}" for match in disallowed) + "\n"
            return 1, stdout, ""
        stdout = "\n".join(
            ["Allowed event-scoped recovery references:"]
            + [f"{match['path']}:{match['line']}:{match['matched_pattern']}" for match in allowed]
        ).rstrip() + "\n"
        return 0, stdout, ""
    return 1, "", f"Unknown scan purpose: {spec.purpose}\n"


def _scan_recovery_tool_matches() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    allowed_relatives = {
        "07 - MCP Server/mcp_server/semantic_control_kernel_visibility.py",
        "Client Frontend/client_frontend/pipeline_agent/kernel_client.js",
    }
    roots = (
        PIPELINE_ROOT / "Client Frontend" / "client_frontend" / "pipeline_agent",
        PIPELINE_ROOT / "Client Frontend" / "dev-tests" / "tests",
        PIPELINE_ROOT / "07 - MCP Server" / "mcp_server",
    )
    tool_names = (
        "kernel_apply_recovery_option",
        "kernel_open_recovery_dialog",
        "kernel_retry_recoverable_workflow",
        "kernel_resolve_stale_lock",
        "kernel_rebind_database_artifact_tree",
        "kernel_discard_or_archive_staged_work",
        "kernel_reconcile_partial_pipeline_run",
        "kernel_open_support_bundle",
    )
    matcher = re.compile("|".join(re.escape(name) for name in tool_names))
    allowed: list[dict[str, str]] = []
    disallowed: list[dict[str, str]] = []
    for root in roots:
        for candidate in sorted(path for path in root.rglob("*") if _should_scan_file(path)):
            for match in _file_matches(candidate, matcher):
                if match["path"] in allowed_relatives or match["path"].startswith("Client Frontend/dev-tests/tests/"):
                    allowed.append(match)
                else:
                    disallowed.append(match)
    return disallowed, allowed
