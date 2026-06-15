from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SURFACE_IDS = [
    "orchestrator.route_intake_policy",
    "orchestrator.execution_policy",
    "orchestrator.health_dependency_policy",
    "orchestrator.artifact_publication_policy",
]


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "orchestrator_module"
    shutil.copytree(PROJECT_ROOT / "orchestrator", module_root / "orchestrator")
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    shutil.copy2(PROJECT_ROOT / "module-registry.json", module_root / "module-registry.json")
    return module_root


def _invoke(module_root: Path, tmp_path: Path, payload: dict) -> dict:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "orchestrator.edit_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=module_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def _updated_value(surface_id: str, value: dict) -> dict:
    updated = json.loads(json.dumps(value))
    if surface_id == "orchestrator.route_intake_policy":
        updated["enabled_route_families"] = ["Documents"]
    elif surface_id == "orchestrator.execution_policy":
        updated["projection_catalog_timeout_seconds"] = 91
    elif surface_id == "orchestrator.health_dependency_policy":
        updated["fallback_for_other_scopes"] = {"optimizer": {".txt": ["renderer-html"]}}
    else:
        updated["request_file_names"]["interpreter_request"] = "custom.request.json"
    return updated


def test_describe_surfaces_exposes_only_policy_surfaces(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    payload = _invoke(module_root, tmp_path, {"action": "describe_surfaces"})

    assert payload["status"] == "ok"
    assert [surface["surface_id"] for surface in payload["surfaces"]] == SURFACE_IDS
    assert [card["label"] for card in payload["summary_cards"]] == [
        "Routing Snapshot",
        "Execution Snapshot",
        "Health Profiles",
        "Artifact Layout",
    ]
    assert "run- and debug-owned" in payload["module_summary"]
    assert "owner-local policy defaults" in payload["module_summary"]
    assert "snapshot cards" in payload["module_summary"]
    assert "guided working area" in payload["module_summary"]
    assert "state/ui_state.json" in payload["module_summary"]
    for surface in payload["surfaces"]:
        assert surface["kind"] == "policy"
        assert surface["module_key"] == "orchestrator"
        assert surface["storage_kind"] == "json_file"
        assert surface["editable"] is True
        assert surface["editor_kind"] == "nested_policy"
        assert surface["preview"] == ["json", "summary", "diff"]
        assert surface["operation_links"] == []
        assert surface["runtime_impact"] == "next_run"
        assert surface["drift_status"] == "implicit_code_default"
        assert surface["section"] == "Settings"
        assert surface["field_groups"]
        assert surface["field_labels"]
        assert surface["field_help"]


def test_read_bundle_returns_same_surface_set_with_inline_values(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    described = _invoke(module_root, tmp_path, {"action": "describe_surfaces"})
    bundled = _invoke(module_root, tmp_path, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [surface["surface_id"] for surface in bundled["surfaces"]] == SURFACE_IDS
    assert all(isinstance(surface.get("value"), dict) for surface in bundled["surfaces"])
    assert [card["label"] for card in bundled["summary_cards"]] == [card["label"] for card in described["summary_cards"]]


@pytest.mark.parametrize("surface_id", SURFACE_IDS)
def test_edit_contract_roundtrip_reads_validates_and_writes_each_surface(tmp_path: Path, surface_id: str) -> None:
    module_root = _copy_module(tmp_path / surface_id.replace(".", "_"))
    current = _invoke(module_root, tmp_path, {"action": "read_surface", "surface_id": surface_id})
    updated = _updated_value(surface_id, current["value"])

    validated = _invoke(module_root, tmp_path, {"action": "validate_surface", "surface_id": surface_id, "value": updated})
    written = _invoke(module_root, tmp_path, {"action": "write_surface", "surface_id": surface_id, "value": updated})
    reread = _invoke(module_root, tmp_path, {"action": "read_surface", "surface_id": surface_id})

    assert current["status"] == "ok"
    assert validated["status"] == "ok"
    assert written["status"] == "ok"
    assert reread["value"] == validated["value"] == written["value"]


def test_edit_contract_rejects_unknown_surface_and_invalid_payloads(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    current = _invoke(module_root, tmp_path, {"action": "read_surface", "surface_id": SURFACE_IDS[0]})["value"]
    missing = dict(current)
    missing.pop("pdf_routing")
    extra = dict(current)
    extra["unexpected"] = True

    unknown = _invoke(module_root, tmp_path, {"action": "write_surface", "surface_id": "orchestrator.unknown", "value": {}})
    wrong_type = _invoke(module_root, tmp_path, {"action": "write_surface", "surface_id": SURFACE_IDS[0], "value": []})
    missing_key = _invoke(module_root, tmp_path, {"action": "write_surface", "surface_id": SURFACE_IDS[0], "value": missing})
    extra_key = _invoke(module_root, tmp_path, {"action": "write_surface", "surface_id": SURFACE_IDS[0], "value": extra})

    assert unknown["status"] == "error"
    assert "surface_id" in unknown["reason"]
    assert wrong_type["status"] == "error"
    assert "JSON object" in wrong_type["reason"]
    assert missing_key["status"] == "error"
    assert "unexpected or incorrectly sorted fields" in missing_key["reason"]
    assert extra_key["status"] == "error"
    assert "unexpected or incorrectly sorted fields" in extra_key["reason"]

