from __future__ import annotations

from pathlib import Path

import pytest

from .test_integrations_workflow import _modules


def test_interpret_document_forwards_debug_bundle_dir_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = _modules(tmp_path, "interpreter")
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {"status": "ok", "structured_path": "out.json", "debug_bundle_path": "debug/out.debug.json"}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.interpret_document(
        tmp_path / "doc.request.json",
        tmp_path / "doc.structured.json",
        debug_bundle_dir=tmp_path / "runtime" / "debug",
    )

    assert captured["module_key"] == "interpreter"
    assert captured["payload"] == {
        "action": "interpret_document",
        "request_path": str(tmp_path / "doc.request.json"),
        "structured_output_path": str(tmp_path / "doc.structured.json"),
        "debug_bundle_dir": str(tmp_path / "runtime" / "debug"),
        "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
    }
    assert captured["timeout"] == 1800
    assert captured["env_overlay"] is None


def test_normalize_document_forwards_release_payload_when_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = _modules(tmp_path, "normalizer")
    captured: dict[str, object] = {}
    release = {
        "release_id": "semantic_release.default",
        "release_version": "2026-03-28.v6",
        "fingerprint": "sha256:semantic-default",
    }

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {"status": "ok", "output_path": "normalized.json"}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.normalize_document(
        tmp_path / "doc.structured.json",
        tmp_path / "normalized" / "doc.structured.normalized.json",
        release=release,
    )

    assert captured["module_key"] == "normalizer"
    assert captured["payload"] == {
        "action": "normalize_document",
        "structured_path": str(tmp_path / "doc.structured.json"),
        "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
        "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        "release": release,
    }
    assert captured["timeout"] == 1800
    assert captured["env_overlay"] is None
