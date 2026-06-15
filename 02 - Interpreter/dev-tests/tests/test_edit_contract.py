from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _run_contract(tmp_path: Path, payload: dict) -> tuple[dict, Path]:
    app_home = tmp_path / "app-home"
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["INTERPRETER_HOME"] = str(app_home)
    completed = subprocess.run(
        [sys.executable, "-m", "llm_interpreter.edit_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8")), app_home


def test_describe_surfaces_returns_expected_interpreter_bundle(tmp_path: Path) -> None:
    payload, _app_home = _run_contract(tmp_path, {"action": "describe_surfaces"})

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("INTERPRETER HELP")
    assert [surface["surface_id"] for surface in payload["surfaces"]] == [
        "interpreter.runtime_policy_env",
        "interpreter.execution_limits",
        "interpreter.prompt_bundle",
        "interpreter.output_contract_preview",
        "interpreter.debug_capabilities",
    ]
    assert payload["surfaces"][0]["section"] == "Settings"
    assert payload["surfaces"][1]["field_groups"][0]["label"] == "Assets/Runtime"
    assert [link["action"] for link in payload["surfaces"][-1]["operation_links"]] == [
        "interpret_document",
        "healthcheck",
        "debug_run",
        "generate_llm",
    ]


def test_read_bundle_returns_same_surface_set_with_values(tmp_path: Path) -> None:
    described, _app_home = _run_contract(tmp_path, {"action": "describe_surfaces"})
    bundled, _ = _run_contract(tmp_path, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])


def test_runtime_policy_write_preserves_execution_limits(tmp_path: Path) -> None:
    payload, app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.runtime_policy_env"})

    assert payload["status"] == "ok"
    assert payload["value"] == {
        "LOG_LEVEL": "INFO",
        "DEBUG_BUNDLE_DIR": "",
        "PAGE_ASSET_ALLOWED_ROOTS": "",
        "OPENAI_API_BASE_URL": "https://api.openai.com/v1",
    }

    updated = dict(payload["value"])
    updated["LOG_LEVEL"] = "DEBUG"
    updated["DEBUG_BUNDLE_DIR"] = r"C:\debug-bundles"
    updated["PAGE_ASSET_ALLOWED_ROOTS"] = r"C:\allowed-a;C:\allowed-b"
    updated["OPENAI_API_BASE_URL"] = "https://example.test/v1"
    written, _ = _run_contract(tmp_path, {"action": "write_surface", "surface_id": "interpreter.runtime_policy_env", "value": updated})

    env_text = (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert written["status"] == "ok"
    assert written["value"]["OPENAI_API_BASE_URL"] == "https://example.test/v1"
    assert "LOG_LEVEL=DEBUG" in env_text
    assert "MAX_WORKERS=8" in env_text
    assert "TIMEOUT_SECONDS=300" in env_text


def test_execution_limits_validate_and_write_roundtrip(tmp_path: Path) -> None:
    invalid, _app_home = _run_contract(
        tmp_path,
        {"action": "validate_surface", "surface_id": "interpreter.execution_limits", "value": {"MAX_WORKERS": 0}},
    )
    payload, app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.execution_limits"})
    updated = dict(payload["value"])
    updated["MAX_WORKERS"] = "3"
    written, _ = _run_contract(tmp_path, {"action": "write_surface", "surface_id": "interpreter.execution_limits", "value": updated})

    env_text = (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert invalid["status"] == "error"
    assert "execution_limits hat ungueltige Felder" in invalid["reason"]
    assert written["status"] == "ok"
    assert written["value"]["MAX_WORKERS"] == 3
    assert "MAX_WORKERS=3" in env_text
    assert "LOG_LEVEL=INFO" in env_text


def test_prompt_bundle_defaults_write_and_fail_closed_partial_bundle(tmp_path: Path) -> None:
    payload, app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.prompt_bundle"})
    updated = dict(payload["value"])
    updated["user_prompt_rules_md"] += "\nZusatzregel fuer Regressionstest."
    written, _ = _run_contract(tmp_path, {"action": "write_surface", "surface_id": "interpreter.prompt_bundle", "value": updated})

    bundle_dir = app_home / "config" / "prompt_bundle"
    assert payload["status"] == "ok"
    assert set(payload["value"]) == {
        "system_prompt_md",
        "user_prompt_rules_md",
        "output_schema_json",
        "projection_hint_policy_md",
    }
    assert written["status"] == "ok"
    assert (bundle_dir / "system_prompt.md").exists()
    assert (bundle_dir / "output_schema.json").exists()

    for file_path in bundle_dir.iterdir():
        if file_path.name != "system_prompt.md":
            file_path.unlink()
    failed, _ = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.prompt_bundle"})

    assert failed["status"] == "error"
    assert "Prompt-Bundle unvollstaendig" in failed["reason"]


def test_prompt_bundle_rejects_schema_drift_and_read_only_surfaces(tmp_path: Path) -> None:
    payload, _app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.prompt_bundle"})
    invalid_bundle = dict(payload["value"])
    invalid_bundle["output_schema_json"] = json.dumps({"bad": True})
    invalid, _ = _run_contract(
        tmp_path,
        {"action": "validate_surface", "surface_id": "interpreter.prompt_bundle", "value": invalid_bundle},
    )
    preview, _ = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.output_contract_preview"})
    debug, _ = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "interpreter.debug_capabilities"})
    preview_write, _ = _run_contract(
        tmp_path,
        {"action": "write_surface", "surface_id": "interpreter.output_contract_preview", "value": {"bad": True}},
    )
    debug_write, _ = _run_contract(
        tmp_path,
        {"action": "write_surface", "surface_id": "interpreter.debug_capabilities", "value": {"operation_links": []}},
    )

    assert invalid["status"] == "error"
    assert "kanonischen Output-Schema" in invalid["reason"]
    assert preview["status"] == "ok"
    assert "source" in preview["value"]["persisted_output_schema"]["required"]
    assert debug["status"] == "ok"
    assert [link["action"] for link in debug["value"]["operation_links"]] == [
        "interpret_document",
        "healthcheck",
        "debug_run",
        "generate_llm",
    ]
    assert preview_write["status"] == "error"
    assert "read-only" in preview_write["reason"]
    assert debug_write["status"] == "error"
    assert "read-only" in debug_write["reason"]
