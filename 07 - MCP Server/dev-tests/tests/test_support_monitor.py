from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server import support_monitor


@pytest.fixture()
def support_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "support"
    monkeypatch.setattr(support_monitor, "state_root", lambda: root)
    return root


def test_record_event_redacts_secrets_and_groups_incidents(support_root: Path) -> None:
    first = support_monitor.record_event(
        {
            "module_key": "normalizer",
            "action": "compile_release_package",
            "severity": "error",
            "status": "exception",
            "message": f"Failed in {Path.home()} with token sk-supportsecret123456",
            "exception_type": "RuntimeError",
            "stacktrace": f"Traceback\nFile {Path.home()}\\app.py\nRuntimeError: token sk-supportsecret123456",
            "metadata": {"api_key": "plain-secret", "phase": "compile"},
        }
    )
    second = support_monitor.record_event(
        {
            "module_key": "normalizer",
            "action": "compile_release_package",
            "severity": "error",
            "status": "exception",
            "message": f"Failed in {Path.home()} with token sk-supportsecret123456",
            "exception_type": "RuntimeError",
            "stacktrace": f"Traceback\nFile {Path.home()}\\app.py\nRuntimeError: token sk-supportsecret123456",
            "metadata": {"api_key": "plain-secret", "phase": "compile"},
        }
    )

    listed = support_monitor.list_incidents()

    assert first["status"] == "ok"
    assert first["event"]["metadata"]["api_key"] == "[REDACTED]"
    assert "sk-supportsecret" not in json.dumps(first, ensure_ascii=False)
    assert "%USERPROFILE%" in first["event"]["message"]
    assert first["incident"]["incident_id"] == second["incident"]["incident_id"]
    assert listed["incident_count"] == 1
    assert listed["incidents"][0]["event_count"] == 2
    assert (support_root / "support_events.jsonl").exists()


def test_build_submit_and_dismiss_bug_report(support_root: Path) -> None:
    recorded = support_monitor.record_event(
        {
            "module_key": "corpus_builder",
            "action": "activation_preflight",
            "severity": "critical",
            "status": "exception",
            "message": "Activation failed for release default",
            "exception_type": "RuntimeError",
        }
    )
    incident_id = recorded["incident"]["incident_id"]

    preview = support_monitor.preview_bug_report(incident_id=incident_id, user_note="Happened after install")
    built = support_monitor.build_bug_report(incident_id=incident_id, user_note="Happened after install")
    submitted = support_monitor.submit_bug_report(report_path=built["report_path"])
    dismissed = support_monitor.dismiss_incident(incident_id=incident_id, reason="queued")
    active = support_monitor.list_incidents()
    all_incidents = support_monitor.list_incidents(include_dismissed=True)

    assert preview["report"]["incident"]["incident_id"] == incident_id
    assert Path(built["report_path"]).exists()
    assert submitted["status"] == "queued"
    assert Path(submitted["queued_path"]).exists()
    assert dismissed["dismissed"] is True
    assert active["incident_count"] == 0
    assert all_incidents["incident_count"] == 1
    assert (support_root / "outbox" / "submission_log.jsonl").exists()


def test_build_bug_report_rejects_overlong_output_path(support_root: Path, tmp_path: Path) -> None:
    recorded = support_monitor.record_event(
        {
            "module_key": "mcp_server",
            "action": "field_ready_probe",
            "severity": "critical",
            "status": "exception",
            "message": "Support report path budget probe",
        }
    )
    target = _path_at_least(tmp_path, 305) / "report.json"

    with pytest.raises(support_monitor.SupportError, match="Windows path budget"):
        support_monitor.build_bug_report(
            incident_id=recorded["incident"]["incident_id"],
            output_path=str(target),
        )


def test_submit_bug_report_queues_report_id_as_safe_outbox_leaf(support_root: Path) -> None:
    report_path = support_root / "manual-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"report_id": r"..\escape/with:bad*chars", "incident": {"incident_id": "x"}}),
        encoding="utf-8",
    )

    submitted = support_monitor.submit_bug_report(report_path=str(report_path))
    queued = Path(submitted["queued_path"]).resolve()

    assert queued.parent == (support_root / "outbox").resolve()
    assert queued.name == "escape_with_bad_chars.queued.json"
    assert queued.exists()
    assert not (support_root / "escape.queued.json").exists()


def test_submit_bug_report_bounds_long_report_id_filename(support_root: Path) -> None:
    report_path = support_root / "manual-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"report_id": "r" * 200}), encoding="utf-8")

    submitted = support_monitor.submit_bug_report(report_path=str(report_path))
    queued = Path(submitted["queued_path"])

    assert queued.parent.resolve() == (support_root / "outbox").resolve()
    assert len(queued.stem.removesuffix(".queued")) <= 80


def test_support_assessment_requires_reportable_classification(support_root: Path) -> None:
    non_reportable = support_monitor.assess_incident(
        {
            "classification": "missing_path",
            "confidence": "high",
            "module_key": "orchestrator",
            "tool_action": "run_active_pipeline",
            "message": "Workspace path is missing",
        }
    )
    assert non_reportable["reportable"] is False
    assert support_monitor.list_incidents()["event_count"] == 0

    with pytest.raises(support_monitor.SupportError, match="not reportable"):
        support_monitor.require_reportable_assessment(non_reportable["assessment"]["assessment_id"])

    reportable = support_monitor.assess_incident(
        {
            "classification": "unexpected_exception",
            "confidence": "high",
            "module_key": "normalizer",
            "tool_action": "compile_release_package",
            "message": "Compile failed unexpectedly",
            "exception_type": "RuntimeError",
        }
    )
    assessment_id = reportable["assessment"]["assessment_id"]
    assessment = support_monitor.require_reportable_assessment(assessment_id)
    preview = support_monitor.preview_bug_report(incident_id=str(assessment["incident_id"]))
    built = support_monitor.build_bug_report(incident_id=str(assessment["incident_id"]))
    queued = support_monitor.submit_bug_report(report_path=built["report_path"])

    assert preview["report"]["incident"]["incident_id"] == reportable["assessment"]["incident_id"]
    assert queued["status"] == "queued"


def test_unknown_incident_is_rejected(support_root: Path) -> None:
    del support_root

    with pytest.raises(support_monitor.SupportError, match="Unknown incident_id"):
        support_monitor.preview_bug_report(incident_id="missing")


def _path_at_least(root: Path, min_length: int) -> Path:
    path = root
    index = 0
    while len(str(path)) < min_length:
        path = path / f"deepsegment{index:02d}"
        index += 1
    return path
