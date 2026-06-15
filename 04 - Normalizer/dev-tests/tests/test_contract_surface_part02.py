from tests.contract_surface_shared import *  # noqa: F401,F403

def test_main_export_default_blueprint_release_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    output_path = tmp_path / "release" / "default.release.json"
    request_path.write_text(
        json.dumps(
            {
                "action": "export_default_blueprint_release",
                "blueprint_ref": "default",
                "output_path": str(output_path),
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_export(command, *, root):
        captured["command"] = command
        captured["root"] = root
        return {
            "status": "OK",
            "blueprint_ref": "default",
            "output_path": str(output_path),
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "projection_ids": ["housing.default.v1"],
            "fingerprint": "sha256:test",
        }

    monkeypatch.setattr(
        workflow,
        "export_default_blueprint_release_response",
        fake_export,
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["blueprint_ref"] == "default"
    assert captured["root"] == PROJECT_ROOT
    assert captured["command"] == validation.ExportDefaultBlueprintReleaseCommand(
        blueprint_ref="default",
        output_path=output_path,
    )

def test_main_create_zero_shot_working_release_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    output_path = tmp_path / "release" / "zero.release.json"
    request_path.write_text(
        json.dumps(
            {
                "action": "create_zero_shot_working_release",
                "blueprint_ref": "default",
                "target_locale": "en",
                "output_path": str(output_path),
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_zero(command, *, root):
        captured["command"] = command
        captured["root"] = root
        return {"status": "OK", "blueprint_ref": "default", "output_path": str(output_path)}

    monkeypatch.setattr(workflow, "create_zero_shot_working_release_response", fake_zero)

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert captured["root"] == PROJECT_ROOT
    assert captured["command"] == validation.CreateZeroShotWorkingReleaseCommand(
        blueprint_ref="default",
        target_locale="en",
        output_path=output_path,
    )

def test_main_debug_run_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")
    request_path.write_text(
        json.dumps(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(session_root),
                "output_root": str(output_root),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_debug(payload, *, root: Path, parse_debug_run_command_fn):  # noqa: ANN001
        captured["payload"] = payload
        captured["root"] = root
        captured["parse_debug_run_command_fn"] = parse_debug_run_command_fn
        return {"status": "ok", "summary": "done", "outputs": {"normalized_outputs": []}, "metrics": {}}

    monkeypatch.setattr(workflow.debug_workflow, "run_debug", fake_run_debug)

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert captured["root"] == PROJECT_ROOT
    assert captured["payload"]["action"] == "debug_run"
    assert captured["parse_debug_run_command_fn"] is validation.parse_debug_run_command

def test_main_unknown_action_returns_error(tmp_path: Path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "unknown"}), encoding="utf-8")

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ERROR"
    assert "Unbekannte Aktion" in payload["error"]

def test_python_m_module_path_stays_startable(tmp_path: Path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "unknown"}), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "normalizer_vision.orchestrator_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert completed.returncode == 0
    assert payload["status"] == "ERROR"
