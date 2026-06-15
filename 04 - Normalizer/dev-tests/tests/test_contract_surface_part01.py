from tests.contract_surface_shared import *  # noqa: F401,F403

def test_main_normalize_document_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    structured_path = tmp_path / "doc.structured.json"
    normalized_output_path = tmp_path / "normalized" / "doc.structured.normalized.json"
    structured_path.write_text("{}", encoding="utf-8")
    request_path.write_text(
        json.dumps(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(normalized_output_path),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_normalize_document(command, *, root: Path) -> dict:
        captured["command"] = command
        captured["root"] = root
        return {"status": "OK", "output_path": "out.json", "needs_review": False, "message": "", "review_reason": ""}

    monkeypatch.setattr(workflow, "normalize_document", fake_normalize_document)

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert captured["root"] == PROJECT_ROOT
    assert captured["command"] == validation.NormalizeDocumentCommand(
        structured_path=structured_path,
        normalized_output_path=normalized_output_path,
        request_output_path=None,
        runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=12000),
    )

def test_main_healthcheck_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"action": "healthcheck", "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(workflow, "healthcheck", lambda command, *, root: {"status": "OK", "healthy": True, "dependencies": []})

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["healthy"] is True

def test_main_build_projection_catalog_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "build_projection_catalog"}), encoding="utf-8")
    monkeypatch.setattr(
        workflow,
        "build_projection_catalog_response",
        lambda *, root: {"status": "OK", "projection_catalog": {"catalog_version": "sha256:test", "master_taxonomy_version": "v1", "projections": []}},
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["projection_catalog"]["catalog_version"] == "sha256:test"

def test_main_build_runtime_semantic_assets_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    release = build_semantic_release(PROJECT_ROOT)
    request_path.write_text(
        json.dumps(
            {
                "action": "build_runtime_semantic_assets",
                "release": release,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        workflow,
        "build_runtime_semantic_assets_response",
        lambda command: {
            "status": "OK",
            "runtime_semantic_assets": {
                "schema_version": "runtime_semantic_assets_v1",
                "release_fingerprint": command.release["fingerprint"],
            },
        },
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["runtime_semantic_assets"]["schema_version"] == "runtime_semantic_assets_v1"

def test_main_publish_semantic_release_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    output_path = tmp_path / "release" / "custom.release.json"
    request_path.write_text(json.dumps({"action": "publish_semantic_release", "output_path": str(output_path)}), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_publish(command, *, root):
        captured["command"] = command
        return {
            "status": "OK",
            "output_path": str(output_path),
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "projection_ids": ["housing.default.v1"],
            "fingerprint": "sha256:test",
        }

    monkeypatch.setattr(
        workflow,
        "publish_semantic_release_response",
        fake_publish,
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["fingerprint"] == "sha256:test"
    assert captured["command"] == validation.PublishSemanticReleaseCommand(output_path=output_path)

def test_main_list_default_blueprints_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "list_default_blueprints"}), encoding="utf-8")
    monkeypatch.setattr(
        workflow,
        "list_default_blueprints_response",
        lambda *, root: {
            "status": "OK",
            "blueprints": [{"blueprint_ref": "default", "label": "Default Canonical"}],
        },
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["blueprints"][0]["blueprint_ref"] == "default"
