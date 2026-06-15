from __future__ import annotations

from pathlib import Path

import pytest

from normalizer_vision.main import main
from normalizer_vision.main.surface import build_parser


def _disable_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("normalizer_vision.main._setup_logging", lambda: None)


def test_parser_exposes_only_headless_maintenance_commands() -> None:
    commands = build_parser()._subparsers._group_actions[0].choices
    assert sorted(commands) == ["analyze-taxonomy", "check-config"]


@pytest.mark.parametrize(
    ("loader", "expected_code", "expected_text"),
    [
        (lambda _config: (_ for _ in ()).throw(ValueError("kaputt")), 1, "Config invalid: kaputt"),
        (lambda _config: type("DummyNormalizer", (), {"profile": type("Profile", (), {"projection_id": "housing.default.v1"})()})(), 0, "Config is valid. Profile: housing.default.v1"),
    ],
)
def test_main_check_config_reports_status(monkeypatch, capsys, loader, expected_code: int, expected_text: str):
    _disable_logging(monkeypatch)
    monkeypatch.setattr("normalizer_vision.main._load_normalizer", loader)

    result = main(["check-config"])
    captured = capsys.readouterr()

    assert result == expected_code
    assert expected_text in captured.out


@pytest.mark.parametrize(
    "command",
    ["normalize", "normalize-batch", "show-prompt", "test-connection", "publish-release", "--gui"],
)
def test_parser_rejects_removed_local_commands(command: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([command])


def test_main_analyze_taxonomy_dispatches_to_workflow(monkeypatch, capsys):
    _disable_logging(monkeypatch)
    calls: dict[str, object] = {}

    def fake_load_master(root: Path) -> dict[str, str]:
        calls["project_root"] = root
        return {"taxonomy_id": "master"}

    def fake_load_projections(root: Path) -> dict[str, dict]:
        calls["projection_root"] = root
        return {"housing.default.v1": {}}

    monkeypatch.setattr(
        "normalizer_vision.main.workflow.load_master_taxonomy_payload",
        fake_load_master,
    )
    monkeypatch.setattr(
        "normalizer_vision.main.workflow.load_local_projection_payloads",
        fake_load_projections,
    )
    monkeypatch.setattr(
        "normalizer_vision.main.workflow.analyze_taxonomy_shape",
        lambda master, projections: {"master": master, "projections": list(projections)},
    )
    monkeypatch.setattr(
        "normalizer_vision.main.workflow.build_semantic_release",
        lambda root: {"release_id": "semantic_release.default", "fingerprint": "sha256:preview"},
    )

    result = main(["analyze-taxonomy"])
    captured = capsys.readouterr()

    assert result == 0
    assert isinstance(calls["project_root"], Path)
    assert "sha256:preview" in captured.out


def test_main_analyze_taxonomy_reports_failures(monkeypatch, capsys):
    _disable_logging(monkeypatch)
    monkeypatch.setattr(
        "normalizer_vision.main.workflow.load_master_taxonomy_payload",
        lambda _root: (_ for _ in ()).throw(RuntimeError("broken taxonomy")),
    )

    result = main(["analyze-taxonomy"])
    captured = capsys.readouterr()

    assert result == 1
    assert "broken taxonomy" in captured.out
