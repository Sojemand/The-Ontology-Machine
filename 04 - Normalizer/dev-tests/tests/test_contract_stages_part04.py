from tests.contract_stages_shared import *  # noqa: F401,F403

def test_validation_rejects_normalized_output_path_without_json_suffix(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="normalized_output_path muss eine JSON-Datei sein"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.txt"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            }
        )

def test_validation_rejects_missing_runtime_settings(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="runtime_settings fehlt"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
            }
        )

def test_workflow_wraps_normalizer_exceptions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.workflow.DocumentNormalizer.from_project",
        staticmethod(lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))),
    )

    result = workflow.normalize_document(
        validation.NormalizeDocumentCommand(
            structured_path=structured_path,
            normalized_output_path=tmp_path / "normalized" / "doc.structured.normalized.json",
            request_output_path=None,
            runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=12000),
        ),
        root=PROJECT_ROOT,
    )

    assert result == {"status": "ERROR", "error": "boom"}

def test_adapter_write_response_uses_atomic_json_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_atomic_json_write(path: Path, payload: dict) -> None:
        captured["path"] = path
        captured["payload"] = payload

    monkeypatch.setattr("normalizer_vision.orchestrator_contract.adapter.atomic_json_write", fake_atomic_json_write)

    response_path = tmp_path / "response.json"
    payload = {"status": "OK", "message": "done"}
    adapter.write_response(response_path, payload)

    assert captured == {"path": response_path, "payload": payload}
