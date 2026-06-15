from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mcp_server import atomic_io, permissions, semantic_control_kernel_client as kernel_client, support_monitor
from mcp_server.orchestrator_contract import main as healthcheck_main
from mcp_server.tool_handler_contracts import _ensure_workspace_normalizer_home
from mcp_server.tools import ToolFailure, call_tool


def test_atomic_json_write_preserves_existing_target_on_replace_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "state.json"
    target.write_text('{"previous": true}', encoding="utf-8")
    captured: list[Path] = []

    def fail_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        captured.append(Path(src))
        raise PermissionError("locked")

    monkeypatch.setattr(atomic_io.os, "replace", fail_replace)

    with pytest.raises(PermissionError):
        atomic_io.atomic_json_write(target, {"new": True})

    assert target.read_text(encoding="utf-8") == '{"previous": true}'
    assert captured and not captured[0].exists()
    assert captured[0].parent == target.parent
    assert captured[0].name != "state.json.tmp"


def test_permission_policy_write_uses_unique_temp_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(permissions, "POLICY_PATH", tmp_path / "config" / "agent_permissions.json")
    real_replace = atomic_io.os.replace
    temp_names: list[str] = []

    def capture_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        temp_names.append(Path(src).name)
        real_replace(src, dst)

    monkeypatch.setattr(atomic_io.os, "replace", capture_replace)

    permissions.write_policy(permissions.default_policy())

    assert len(temp_names) == 1
    assert temp_names[0].startswith(".")
    assert temp_names[0].endswith(".tmp")
    assert temp_names[0] != "agent_permissions.json.tmp"


def test_support_report_replaces_existing_final_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    support_root = tmp_path / "support"
    monkeypatch.setattr(support_monitor, "state_root", lambda: support_root)
    target = tmp_path / "report.json"
    sibling_link = tmp_path / "report-linked.json"
    target.write_text('{"old": true}', encoding="utf-8")
    try:
        os.link(target, sibling_link)
    except OSError as exc:
        pytest.skip(f"hardlink probe unavailable: {exc}")
    recorded = support_monitor.record_event(
        {
            "module_key": "mcp_server",
            "action": "field_ready_probe",
            "severity": "critical",
            "status": "exception",
            "message": "field-ready support report probe",
        }
    )

    support_monitor.build_bug_report(
        incident_id=recorded["incident"]["incident_id"],
        output_path=str(target),
    )

    assert json.loads(target.read_text(encoding="utf-8"))["incident"]["incident_id"]
    assert sibling_link.read_text(encoding="utf-8") == '{"old": true}'


def test_prepare_workspace_rejects_overlong_artifact_folder(tmp_path: Path) -> None:
    artifact_path = _path_at_least(tmp_path, 320)

    with pytest.raises(ToolFailure, match="Windows-Pfadbudget"):
        call_tool("prepare_pipeline_workspace_root", {"artifact_folder": str(artifact_path)})


def test_workspace_reset_confirmation_rejects_overlong_generated_filename(tmp_path: Path) -> None:
    artifact_root = tmp_path / "workspace"
    (artifact_root / "Corpus").mkdir(parents=True)

    with pytest.raises(ToolFailure, match="Windows-Pfadbudget"):
        call_tool(
            "write_workspace_db_reset_confirmation",
            {
                "artifact_folder": str(artifact_root),
                "database_name": "d" * 230,
                "confirm_reset": True,
                "reset_reason": "field-ready path budget probe",
            },
        )


def test_workspace_normalizer_copy_rejects_deep_target_before_copy(tmp_path: Path) -> None:
    artifact_path = _path_at_least(tmp_path, 185)

    with pytest.raises(ToolFailure, match="Windows-Pfadbudget"):
        _ensure_workspace_normalizer_home(artifact_path)

    assert not artifact_path.exists()


def test_healthcheck_response_replaces_existing_final_path(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    sibling_link = tmp_path / "response-linked.json"
    response_path.write_text('{"old": true}', encoding="utf-8")
    try:
        os.link(response_path, sibling_link)
    except OSError as exc:
        pytest.skip(f"hardlink probe unavailable: {exc}")

    assert healthcheck_main(["--response", str(response_path)]) == 0

    assert json.loads(response_path.read_text(encoding="utf-8"))["status"] == "ok"
    assert sibling_link.read_text(encoding="utf-8") == '{"old": true}'


@pytest.mark.parametrize("field,value", [("call_timeout_seconds", 0), ("startup_timeout_seconds", "abc")])
def test_kernel_bridge_timeout_config_is_field_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    kernel_root = tmp_path / "08 - Semantic Control Kernel"
    (kernel_root / "semantic_control_kernel").mkdir(parents=True)
    (kernel_root / "semantic_control_kernel" / "orchestrator_contract.py").write_text("", encoding="utf-8")
    (kernel_root / "runtime" / "python").mkdir(parents=True)
    (kernel_root / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (kernel_root / "module-manifest.json").write_text(
        json.dumps(
            {
                "runtime_dir": "runtime/python",
                "contract_module": "semantic_control_kernel.orchestrator_contract",
            }
        ),
        encoding="utf-8",
    )
    bridge_config = tmp_path / "bridge.json"
    bridge_config.write_text(
        json.dumps(
            {
                "schema_version": kernel_client.BRIDGE_CONFIG_SCHEMA_VERSION,
                "enabled": True,
                "semantic_control_kernel": {
                    "module_root": str(kernel_root),
                    "contract_module": "semantic_control_kernel.orchestrator_contract",
                    field: value,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(kernel_client, "BRIDGE_CONFIG_PATH", bridge_config)

    with pytest.raises(kernel_client.SemanticControlKernelClientError, match=field):
        kernel_client._load_bridge_config()


def _path_at_least(root: Path, min_length: int) -> Path:
    path = root
    index = 0
    while len(str(path)) < min_length:
        path = path / f"deepsegment{index:02d}"
        index += 1
    return path
