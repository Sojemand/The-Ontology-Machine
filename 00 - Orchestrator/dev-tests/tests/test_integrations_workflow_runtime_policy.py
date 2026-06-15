from __future__ import annotations

from pathlib import Path

import pytest

from .test_integrations_workflow import _modules


def test_extract_document_to_targets_forwards_runtime_policy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = _modules(tmp_path, "optimizer")
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {"status": "ok", "document_raw_path": "out.raw.json", "page_raw_paths": ["out.raw.json"], "page_asset_paths": []}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.extract_document_to_targets(
        tmp_path / "doc.pdf",
        tmp_path / "optimizer" / "raw_extracts" / "doc.raw.json",
        tmp_path / "optimizer" / "page_images" / "doc.abcd1234",
        logical_source_path="queue/doc.pdf",
        runtime_policy_path=tmp_path / "runtime" / "runtime_semantic_assets.json",
    )

    assert captured["module_key"] == "optimizer"
    assert captured["payload"] == {
        "action": "extract_document",
        "source_path": str(tmp_path / "doc.pdf"),
        "raw_output_path": str(tmp_path / "optimizer" / "raw_extracts" / "doc.raw.json"),
        "page_assets_dir": str(tmp_path / "optimizer" / "page_images" / "doc.abcd1234"),
        "logical_source_path": "queue/doc.pdf",
        "runtime_policy_path": str(tmp_path / "runtime" / "runtime_semantic_assets.json"),
    }
    assert captured["timeout"] == 1800
    assert captured["env_overlay"] is None

