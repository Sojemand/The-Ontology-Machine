from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
MCP_SERVER_ROOT = PIPELINE_ROOT / "07 - MCP Server"
CLIENT_FRONTEND_ROOT = PIPELINE_ROOT / "Client Frontend"
GO_LIVE_BUNDLE_ROOT = MODULE_ROOT / "tools" / "go_live_bundle"

FORBIDDEN_PATTERN = (
    r"mcp_server\.semantic_kernel|from \.semantic_kernel|mcp_server/semantic_kernel|"
    r"tool_catalog_semantic_kernel|tool_handlers_semantic_kernel|KERNEL_TOOL_NAMES|"
    r"llm_action_catalog|open_workflow|inspect_workflow|execute_readonly_workflow_action|"
    r"execute_author_workflow_action|execute_operator_workflow_action|execute_admin_workflow_action|"
    r"interrupt_workflow|close_workflow|workflow_family_id|workflow_revision|action_token|"
    r"target_action_id|x_action_catalog|required_agent_level|permission-level execute"
)

ACTIVE_SCAN_ROOTS = (
    Path("07 - MCP Server/mcp_server"),
    Path("07 - MCP Server/config"),
    Path("07 - MCP Server/runtime"),
    Path("07 - MCP Server/module-manifest.json"),
    Path("07 - MCP Server/README.md"),
    Path("Client Frontend/client_frontend"),
    Path("Client Frontend/server"),
    Path("Client Frontend/src"),
    Path("Client Frontend/README.md"),
    Path("08 - Semantic Control Kernel/semantic_control_kernel"),
    Path("08 - Semantic Control Kernel/module-manifest.json"),
    Path("08 - Semantic Control Kernel/README.md"),
)

PHASE19_REQUIRED_KERNEL_TESTS = (
    MODULE_ROOT / "dev-tests" / "tests" / "test_phase19_pipeline_owner_capabilities.py",
    MODULE_ROOT / "dev-tests" / "tests" / "test_phase19_adapter_unblock.py",
    MODULE_ROOT / "dev-tests" / "tests" / "test_phase19_pipeline_e2e_smoke.py",
)

GENERATED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".venv", "venv"}
PHASE20_TRUTH_INPUTS: tuple[Path, ...] = (
    MODULE_ROOT / "tools" / "generate_go_live_bundle.py",
    GO_LIVE_BUNDLE_ROOT / "__init__.py",
    GO_LIVE_BUNDLE_ROOT / "paths.py",
    GO_LIVE_BUNDLE_ROOT / "command_matrix.py",
    GO_LIVE_BUNDLE_ROOT / "command_runner.py",
    GO_LIVE_BUNDLE_ROOT / "command_records.py",
    GO_LIVE_BUNDLE_ROOT / "process_execution.py",
    GO_LIVE_BUNDLE_ROOT / "scans.py",
    GO_LIVE_BUNDLE_ROOT / "fixtures.py",
    GO_LIVE_BUNDLE_ROOT / "client_events.py",
    GO_LIVE_BUNDLE_ROOT / "client_event_snapshot.py",
    GO_LIVE_BUNDLE_ROOT / "support_runtime.py",
    GO_LIVE_BUNDLE_ROOT / "surface_snapshots.py",
    GO_LIVE_BUNDLE_ROOT / "support_samples.py",
    GO_LIVE_BUNDLE_ROOT / "evidence_reports.py",
    GO_LIVE_BUNDLE_ROOT / "blockers.py",
    GO_LIVE_BUNDLE_ROOT / "bundle_reports.py",
    GO_LIVE_BUNDLE_ROOT / "e2e_matrix.py",
    GO_LIVE_BUNDLE_ROOT / "phase19_evidence.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "agent_tools.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "client_frontend_bridge.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "event_scoped_tools.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "mcp_tool_schemas.py",
    MODULE_ROOT / "semantic_control_kernel" / "services" / "kernel_mirror_event_service.py",
    MODULE_ROOT / "semantic_control_kernel" / "services" / "user_interaction_service.py",
    MODULE_ROOT / "semantic_control_kernel" / "repository" / "event_store.py",
    MODULE_ROOT / "semantic_control_kernel" / "repository" / "support_bundles.py",
    MCP_SERVER_ROOT / "mcp_server" / "semantic_control_kernel_visibility.py",
    MCP_SERVER_ROOT / "mcp_server" / "tool_catalog_semantic_control_kernel.py",
    MCP_SERVER_ROOT / "mcp_server" / "semantic_control_kernel_client_frontend_bridge.py",
    CLIENT_FRONTEND_ROOT / "client_frontend" / "pipeline_agent" / "kernel_client.js",
)


def _default_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"glv_{stamp}"


def _git_head_sha() -> str:
    return _run_git("rev-parse", "HEAD").strip()


def _source_commit_marker() -> str:
    sha = _git_head_sha() or "unknown"
    dirty = bool(_git_status_short().strip())
    return f"{sha}+uncommitted_worktree" if dirty else sha


def phase20_truth_hash() -> str:
    digest = hashlib.sha256()
    for path in PHASE20_TRUTH_INPUTS:
        digest.update(path.relative_to(PIPELINE_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        if not path.exists():
            digest.update(b"[missing]")
            digest.update(b"\0")
            continue
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_status_short() -> str:
    return _run_git("status", "--short")


def _run_git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=PIPELINE_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return ""
    return completed.stdout if completed.returncode == 0 else ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _decision_from_results(blockers: list[dict[str, str]], command_records: list[dict[str, Any]]) -> str:
    if not command_records:
        return "not_ready"
    if blockers:
        return "not_ready"
    if any(record["result"] != "pass" for record in command_records):
        return "not_ready"
    return "ready"


def _json_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _mkdir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
