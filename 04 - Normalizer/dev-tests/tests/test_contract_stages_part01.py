from tests.contract_stages_shared import *  # noqa: F401,F403

def test_workflow_normalize_document_passes_runtime_settings_and_release(
    tmp_project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    release = build_semantic_release(tmp_project_root)

    class DummyNormalizer:
        def normalize(
            self,
            structured_path: Path,
            normalized_output_path: Path,
            *,
            request_output_path: Path | None = None,
        ) -> NormalizationResult:
            captured["structured_path"] = structured_path
            captured["normalized_output_path"] = normalized_output_path
            captured["request_output_path"] = request_output_path
            return NormalizationResult(
                input_path=str(structured_path),
                output_path=str(normalized_output_path),
                status="OK",
                needs_review=False,
                duration_ms=12,
                message="normalized",
                review_reason="",
            )

    def fake_from_project(project_root: Path, *, runtime_settings=None, provider=None, config_path=None, semantic_release=None):
        captured["project_root"] = project_root
        captured["runtime_settings"] = runtime_settings
        captured["semantic_release"] = semantic_release
        return DummyNormalizer()

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.workflow.DocumentNormalizer.from_project",
        staticmethod(fake_from_project),
    )
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    normalized_output_path = tmp_path / "normalized" / "doc.structured.normalized.json"

    result = workflow.normalize_document(
        validation.NormalizeDocumentCommand(
            structured_path=structured_path,
            normalized_output_path=normalized_output_path,
            request_output_path=None,
            runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=12000),
            release=release,
        ),
        root=tmp_project_root,
    )

    assert captured["project_root"] == tmp_project_root
    assert captured["runtime_settings"] == NormalizerRuntimeSettings(model="gpt-5.4", max_output_tokens=12000)
    assert captured["semantic_release"] == release
    assert captured["structured_path"] == structured_path
    assert captured["normalized_output_path"] == normalized_output_path
    assert captured["request_output_path"] is None
    assert result["status"] == "OK"
    assert result["output_path"] == str(normalized_output_path)
    assert result["review_reason"] == ""

def test_validation_accepts_runtime_settings():
    assert validation.parse_runtime_settings({"runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000}}) == validation.RuntimeSettings(
        model="gpt-5.4",
        max_output_tokens=12000,
    )

def test_validation_rejects_legacy_overrides_in_normalize_document(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="overrides wird nicht mehr akzeptiert"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
                "overrides": {"model": "gpt-5.4"},
            }
        )

def test_validation_rejects_unknown_fields_in_normalize_document(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unbekannte Felder: extra"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
                "extra": True,
            }
        )

def test_validation_accepts_release_in_normalize_document(tmp_project_root: Path, tmp_path: Path) -> None:
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    release = build_semantic_release(tmp_project_root)

    command = validation.parse_normalize_document_command(
        {
            "action": "normalize_document",
            "structured_path": str(structured_path),
            "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            "release": release,
        }
    )

    assert command.release is not None
    assert command.release["fingerprint"] == release["fingerprint"]

def test_validation_rejects_legacy_overrides_in_healthcheck():
    with pytest.raises(ValueError, match="overrides wird nicht mehr akzeptiert"):
        validation.parse_healthcheck_command(
            {
                "action": "healthcheck",
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
                "overrides": {"model": "gpt-5.4"},
            }
        )

def test_validation_rejects_unknown_fields_in_healthcheck():
    with pytest.raises(ValueError, match="Unbekannte Felder: extra"):
        validation.parse_healthcheck_command(
            {
                "action": "healthcheck",
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
                "extra": True,
            }
        )

def test_workflow_healthcheck_surfaces_provider_state(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class DummyProvider:
        provider_name = "openai_oauth"

        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            captured["messages"] = messages
            captured["schema"] = schema
            captured["max_output_tokens"] = max_output_tokens
            captured["thinking_effort"] = thinking_effort
            return '{"accepted":true}'

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.workflow.create_provider",
        lambda config: captured.setdefault("config", config) and DummyProvider(),
    )

    result = workflow.healthcheck(
        validation.HealthcheckCommand(runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=15000)),
        root=PROJECT_ROOT,
    )

    assert result["status"] == "OK"
    assert result["healthy"] is True
    assert result["dependencies"][0]["healthy"] is True
    assert result["dependencies"][0]["detail"] == "openai_oauth (gpt-5.4, max_output_tokens=15000, reasoning=none)"
    assert captured["schema"] is None
    assert captured["max_output_tokens"] == 15000
    assert captured["thinking_effort"] == "none"
    assert captured["config"].taxonomy_profile_id == "housing.default.v1"
    assert "json" in "\n".join(str(message["content"]).lower() for message in captured["messages"])

def test_workflow_healthcheck_redacts_runtime_secrets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.workflow.create_provider",
        lambda _config: (_ for _ in ()).throw(RuntimeError('Bearer oauth-secret-123 {"access_token":"oauth-secret-123"}')),
    )

    result = workflow.healthcheck(
        validation.HealthcheckCommand(runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=15000)),
        root=PROJECT_ROOT,
    )

    detail = result["dependencies"][0]["detail"]
    assert result["status"] == "ERROR"
    assert "oauth-secret-123" not in detail
    assert "Bearer [REDACTED]" in detail
