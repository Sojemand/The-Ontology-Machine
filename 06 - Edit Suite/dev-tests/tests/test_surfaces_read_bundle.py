from __future__ import annotations

import importlib
from pathlib import Path

from edit_suite.registry.types import ModuleReadinessEntry

bundle_workflow = importlib.import_module("edit_suite.surfaces.load_bundle")


def _entry() -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name="01 - Optimizer",
        display_name="Optimizer",
        module_root="C:/ImageOptimizer",
        module_key="optimizer",
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path="ingestion_layer_vision/edit_contract",
        runtime_available=True,
    )


def test_load_bundle_prefers_read_bundle_when_owner_supports_it(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        calls.append(payload["action"])
        if payload["action"] != "read_bundle":
            raise AssertionError(f"unexpected legacy action: {payload['action']}")
        return {
            "status": "ok",
            "module_summary": "summary",
            "surfaces": [
                {
                    "surface_id": "optimizer.settings",
                    "label": "Settings",
                    "kind": "settings",
                    "editable": True,
                    "source_path": "config/config.yaml",
                    "section": "Settings",
                    "value": {"parallel_workers": 2},
                }
            ],
        }

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(_entry(), state_root=tmp_path)

    assert calls == ["read_bundle"]
    assert bundle.module_summary == "summary"
    assert bundle.surfaces[0].value["parallel_workers"] == 2


def test_load_bundle_falls_back_to_legacy_actions_when_read_bundle_is_unknown(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        calls.append(payload["action"])
        if payload["action"] == "read_bundle":
            return {"status": "error", "reason": "unknown action"}
        if payload["action"] == "describe_surfaces":
            return {
                "status": "ok",
                "module_summary": "legacy",
                "surfaces": [{"surface_id": "optimizer.settings", "label": "Settings", "kind": "settings", "editable": True, "source_path": "config/config.yaml", "section": "Settings"}],
            }
        return {"status": "ok", "value": {"parallel_workers": 4}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(_entry(), state_root=tmp_path)

    assert calls == ["read_bundle", "describe_surfaces", "read_surface"]
    assert bundle.module_summary == "legacy"
    assert bundle.surfaces[0].value["parallel_workers"] == 4


def test_load_bundle_does_not_hide_read_bundle_contract_errors(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        calls.append(payload["action"])
        if payload["action"] == "read_bundle":
            return {"status": "error", "reason": "schema mismatch in read_bundle"}
        raise AssertionError(f"legacy fallback must not run: {payload['action']}")

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)

    try:
        bundle_workflow.load_bundle(_entry(), state_root=tmp_path)
    except ValueError as exc:
        assert "schema mismatch" in str(exc)
    else:
        raise AssertionError("read_bundle contract errors must stay visible")

    assert calls == ["read_bundle"]


def test_load_bundle_does_not_treat_domain_not_supported_as_legacy_unknown_action(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        calls.append(payload["action"])
        if payload["action"] == "read_bundle":
            return {"status": "error", "reason": "database format not supported for this release"}
        raise AssertionError(f"legacy fallback must not run: {payload['action']}")

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)

    try:
        bundle_workflow.load_bundle(_entry(), state_root=tmp_path)
    except ValueError as exc:
        assert "database format not supported" in str(exc)
    else:
        raise AssertionError("domain read_bundle errors must stay visible")

    assert calls == ["read_bundle"]


def test_load_bundle_preserves_owner_reported_load_errors_from_read_bundle(tmp_path: Path, monkeypatch) -> None:
    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        assert payload["action"] == "read_bundle"
        return {
            "status": "ok",
            "module_summary": "summary",
            "surfaces": [{"surface_id": "optimizer.settings", "label": "Settings", "kind": "settings", "editable": True, "source_path": "config/config.yaml", "section": "Settings", "load_error": "yaml missing"}],
        }

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(_entry(), state_root=tmp_path)

    assert bundle.surfaces[0].load_error == "yaml missing"
    assert bundle.surfaces[0].editable is False

