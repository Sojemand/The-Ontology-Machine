from tests.contract_debug_run_shared import *  # noqa: F401,F403

def test_debug_run_single_writes_session_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_from_project(project_root: Path, *, runtime_settings=None, provider=None, config_path=None):
        del provider, config_path
        captured["project_root"] = project_root
        captured["runtime_settings"] = runtime_settings
        return _DummyNormalizer()

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.debug_workflow.DocumentNormalizer.from_project",
        staticmethod(fake_from_project),
    )

    result = workflow.dispatch(
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "source_path": str(source_path),
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        },
        root=PROJECT_ROOT,
        require_action_fn=validation.require_action,
        parse_normalize_document_command_fn=validation.parse_normalize_document_command,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        parse_build_runtime_semantic_assets_command_fn=validation.parse_build_runtime_semantic_assets_command,
        parse_publish_semantic_release_command_fn=validation.parse_publish_semantic_release_command,
        parse_list_default_blueprints_command_fn=validation.parse_list_default_blueprints_command,
        parse_export_default_blueprint_release_command_fn=validation.parse_export_default_blueprint_release_command,
        parse_create_zero_shot_working_release_command_fn=validation.parse_create_zero_shot_working_release_command,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    session_result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))
    run_log = (session_root / "run.log").read_text(encoding="utf-8")

    assert captured["project_root"] == PROJECT_ROOT
    assert captured["runtime_settings"] == NormalizerRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=15000)
    assert result["status"] == "ok"
    assert snapshot["status"] == "ok"
    assert snapshot["stage"] == "Normalizer"
    assert session_result["outputs"]["normalized_outputs"] == ["outputs/normalized/doc.structured.normalized.json"]
    assert "[RUN] normalizer debug_run gestartet" in run_log
    assert "[OK] doc.structured.json" in run_log

def test_debug_run_batch_preserves_relative_output_parents_and_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    input_root = tmp_path / "structured"
    (input_root / "sub").mkdir(parents=True)
    (input_root / "sub" / "review_a.structured.json").write_text("{}", encoding="utf-8")
    (input_root / "bad_b.structured.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.debug_workflow.DocumentNormalizer.from_project",
        staticmethod(lambda *_args, **_kwargs: _DummyNormalizer()),
    )

    result = workflow.dispatch(
        {
            "action": "debug_run",
            "mode": "batch",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "input_root": str(input_root),
            "worker_count": 2,
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        },
        root=PROJECT_ROOT,
        require_action_fn=validation.require_action,
        parse_normalize_document_command_fn=validation.parse_normalize_document_command,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        parse_build_runtime_semantic_assets_command_fn=validation.parse_build_runtime_semantic_assets_command,
        parse_publish_semantic_release_command_fn=validation.parse_publish_semantic_release_command,
        parse_list_default_blueprints_command_fn=validation.parse_list_default_blueprints_command,
        parse_export_default_blueprint_release_command_fn=validation.parse_export_default_blueprint_release_command,
        parse_create_zero_shot_working_release_command_fn=validation.parse_create_zero_shot_working_release_command,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
    )

    assert result["status"] == "error"
    assert result["metrics"]["documents_total"] == 2
    assert result["metrics"]["error_count"] == 1
    assert result["metrics"]["needs_review_count"] == 2
    assert "outputs/sub/normalized/review_a.structured.normalized.json" in result["outputs"]["normalized_outputs"]

def test_debug_run_cancelled_before_start_writes_cancelled_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")
    session_root.mkdir(parents=True)
    (session_root / "cancel.request").touch()

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.debug_workflow.DocumentNormalizer.from_project",
        staticmethod(lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not start"))),
    )

    result = workflow.dispatch(
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "source_path": str(source_path),
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        },
        root=PROJECT_ROOT,
        require_action_fn=validation.require_action,
        parse_normalize_document_command_fn=validation.parse_normalize_document_command,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        parse_build_runtime_semantic_assets_command_fn=validation.parse_build_runtime_semantic_assets_command,
        parse_publish_semantic_release_command_fn=validation.parse_publish_semantic_release_command,
        parse_list_default_blueprints_command_fn=validation.parse_list_default_blueprints_command,
        parse_export_default_blueprint_release_command_fn=validation.parse_export_default_blueprint_release_command,
        parse_create_zero_shot_working_release_command_fn=validation.parse_create_zero_shot_working_release_command,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))

    assert result["status"] == "cancelled"
    assert snapshot["status"] == "cancelled"

def test_debug_run_cancelled_during_batch_keeps_partial_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    input_root = tmp_path / "structured"
    input_root.mkdir()
    (input_root / "cancel_a.structured.json").write_text("{}", encoding="utf-8")
    (input_root / "keep_b.structured.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.debug_workflow.DocumentNormalizer.from_project",
        staticmethod(lambda *_args, **_kwargs: _DummyNormalizer(session_root=session_root)),
    )

    result = workflow.dispatch(
        {
            "action": "debug_run",
            "mode": "batch",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "input_root": str(input_root),
            "worker_count": 1,
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        },
        root=PROJECT_ROOT,
        require_action_fn=validation.require_action,
        parse_normalize_document_command_fn=validation.parse_normalize_document_command,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        parse_build_runtime_semantic_assets_command_fn=validation.parse_build_runtime_semantic_assets_command,
        parse_publish_semantic_release_command_fn=validation.parse_publish_semantic_release_command,
        parse_list_default_blueprints_command_fn=validation.parse_list_default_blueprints_command,
        parse_export_default_blueprint_release_command_fn=validation.parse_export_default_blueprint_release_command,
        parse_create_zero_shot_working_release_command_fn=validation.parse_create_zero_shot_working_release_command,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
    )

    assert result["status"] == "cancelled"
    assert result["metrics"]["documents_total"] == 1
    assert result["outputs"]["normalized_outputs"] == ["outputs/normalized/cancel_a.structured.normalized.json"]
