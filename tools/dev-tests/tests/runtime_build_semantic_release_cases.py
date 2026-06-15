from __future__ import annotations

import json
import sys

from runtime_build_tooling_support import NORMALIZER_ROOT, TOOLS_ROOT, load_tool_module


def test_export_semantic_release_tool_writes_current_normalizer_release(tmp_path) -> None:
    module = load_tool_module("test_export_semantic_release", TOOLS_ROOT / "export-semantic-release.py")
    output_path = tmp_path / "semantic_release.default.json"
    release = module.export_semantic_release(output_path)

    if str(NORMALIZER_ROOT) not in sys.path:
        sys.path.insert(0, str(NORMALIZER_ROOT))
    from normalizer_vision.semantic_release import build_semantic_release

    expected = build_semantic_release(NORMALIZER_ROOT)
    actual = json.loads(output_path.read_text(encoding="utf-8"))
    expected.pop("created_at", None)
    actual.pop("created_at", None)

    assert release["fingerprint"] == expected["fingerprint"]
    assert actual == expected
    assert actual["projections"][0]["routing"]["surface_signals"]


def test_export_semantic_release_tool_forwards_target_locale(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_export_semantic_release_target_locale", TOOLS_ROOT / "export-semantic-release.py")
    captured = {}

    if str(NORMALIZER_ROOT) not in sys.path:
        sys.path.insert(0, str(NORMALIZER_ROOT))
    import normalizer_vision.semantic_release as semantic_release

    def fake_publish(root, output_path, target_locale=None):
        captured.update(root=root, output_path=output_path, target_locale=target_locale)
        return {"release_id": "semantic_release.default", "release_version": "2026-03-28.v6", "fingerprint": "sha256:test"}

    monkeypatch.setattr(semantic_release, "publish_semantic_release", fake_publish)
    module.export_semantic_release(tmp_path / "semantic_release.en.json", target_locale="en")

    assert captured["root"] == NORMALIZER_ROOT
    assert captured["target_locale"] == "en"
