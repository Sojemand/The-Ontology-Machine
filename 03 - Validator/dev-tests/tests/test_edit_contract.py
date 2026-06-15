from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_contract(tmp_path: Path, payload: dict) -> tuple[dict, Path]:
    app_home = tmp_path / "validator-home"
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["VALIDATOR_VISION_HOME"] = str(app_home)
    completed = subprocess.run(
        [sys.executable, "-m", "validator_vision.edit_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8")), app_home


def test_describe_surfaces_returns_expected_validator_bundle(tmp_path: Path) -> None:
    payload, _app_home = _run_contract(tmp_path, {"action": "describe_surfaces"})

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("VALIDATOR HELP")
    assert [surface["surface_id"] for surface in payload["surfaces"]] == [
        "validator.settings",
        "validator.report_preview_policy",
        "validator.debug_capabilities",
    ]
    assert payload["surfaces"][0]["section"] == "Settings"
    assert [group["label"] for group in payload["surfaces"][0]["field_groups"]] == ["Checks", "Match"]
    assert payload["surfaces"][1]["kind"] == "policy"
    assert payload["surfaces"][2]["section"] == "Operations"
    assert [link["action"] for link in payload["surfaces"][2]["operation_links"]] == [
        "validate_document",
        "healthcheck",
        "debug_run",
    ]


def test_read_bundle_returns_same_surface_set_with_values(tmp_path: Path) -> None:
    described, _app_home = _run_contract(tmp_path, {"action": "describe_surfaces"})
    bundled, _ = _run_contract(tmp_path, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])


def test_settings_surface_roundtrip_preserves_report_policy(tmp_path: Path) -> None:
    payload, app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "validator.settings"})

    assert payload["status"] == "ok"
    assert set(payload["value"]) == {
        "checks.free_text",
        "checks.context_scalars",
        "checks.content_fields",
        "checks.rows",
        "match.scalar_level",
        "match.row_level",
        "match.require_free_text",
        "match.number_tolerance_absolute",
        "match.min_string_length",
        "match.min_compact_length",
        "match.context_fields",
        "match.skip_content_fields",
        "match.skip_row_fields",
        "match.row_anchor_keys",
    }

    updated = dict(payload["value"])
    updated["checks.free_text"] = False
    updated["match.row_level"] = "FAIL"
    updated["match.context_fields"] = ["company", "iban"]
    write_payload, _ = _run_contract(tmp_path, {"action": "write_surface", "surface_id": "validator.settings", "value": updated})

    assert write_payload["status"] == "ok"
    config_payload = json.loads((app_home / "config" / "config.json").read_text(encoding="utf-8"))
    assert config_payload["checks"]["free_text"] is False
    assert config_payload["match"]["row_level"] == "FAIL"
    assert config_payload["match"]["context_fields"] == ["company", "iban"]
    assert config_payload["flag_needs_review"] is True
    assert config_payload["max_issues_per_check"] == 20


def test_report_policy_roundtrip_preserves_validation_settings(tmp_path: Path) -> None:
    payload, app_home = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "validator.report_preview_policy"})

    assert payload["status"] == "ok"
    assert payload["value"] == {"flag_needs_review": True, "max_issues_per_check": 20}

    write_payload, _ = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "validator.report_preview_policy",
            "value": {"flag_needs_review": False, "max_issues_per_check": 7},
        },
    )

    assert write_payload["status"] == "ok"
    config_payload = json.loads((app_home / "config" / "config.json").read_text(encoding="utf-8"))
    assert config_payload["flag_needs_review"] is False
    assert config_payload["max_issues_per_check"] == 7
    assert config_payload["checks"]["rows"] is True
    assert config_payload["match"]["scalar_level"] == "FAIL"


def test_validate_surface_rejects_unknown_values_and_read_only_surfaces(tmp_path: Path) -> None:
    invalid, _app_home = _run_contract(
        tmp_path,
        {
            "action": "validate_surface",
            "surface_id": "validator.settings",
            "value": {"checks.free_text": True},
        },
    )
    readonly, _ = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "validator.debug_capabilities",
            "value": {"operation_links": []},
        },
    )

    assert invalid["status"] == "error"
    assert "fehlende Felder" in invalid["reason"]
    assert readonly["status"] == "error"
    assert "read-only" in readonly["reason"]
