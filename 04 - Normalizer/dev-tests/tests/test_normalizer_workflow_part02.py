from tests.normalizer_workflow_shared import *  # noqa: F401,F403
from normalizer_vision.normalizer.batch_workflow import _build_batch_output_path

def test_normalize_reports_error_for_missing_model_output_sections(
    tmp_project_root,
    sample_structured_file,
    normalizer_runtime_settings,
):
    class MissingSectionProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps({"schema_version": "1.0", "processing": {}, "classification": {}, "context": {}})

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=MissingSectionProvider(),
    )

    result = normalizer.normalize(sample_structured_file, tmp_project_root / "output" / "sample.pdf.structured.normalized.json")

    assert result.status == "ERROR"
    assert "Modellantwort.content fehlt" in result.message

def test_normalize_batch_keeps_relative_subdirectories_under_normalized_folder(
    tmp_project_root,
    sample_batch_dir,
    sample_structured_input,
    mock_provider,
    normalizer_runtime_settings,
):
    nested = sample_batch_dir / "nested"
    nested.mkdir()
    (nested / "nested.pdf.structured.json").write_text(json.dumps(sample_structured_input), encoding="utf-8")
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=mock_provider,
    )

    results = normalizer.normalize_batch(sample_batch_dir, tmp_project_root / "normalized_root", workers=1)

    assert len(results) == 3
    assert (tmp_project_root / "normalized_root" / "nested" / "normalized" / "nested.pdf.structured.normalized.json").exists()

def test_batch_output_path_budgets_long_generated_names():
    structured_dir = Path("C:/workspace/input")
    structured_path = structured_dir / ("deep_" + "x" * 60) / (("invoice_" + "z" * 180) + ".structured.json")
    output_root = Path("C:/workspace/output/session/outputs")

    output_path = _build_batch_output_path(structured_path, structured_dir=structured_dir, output_root=output_root)

    assert len(str(output_path)) <= 259
    assert output_path.name.endswith(".structured.normalized.json")
    assert "z" * 120 not in output_path.name

def test_load_config_stays_auth_free_under_runtime_environment(tmp_project_root, monkeypatch):
    monkeypatch.setenv("VISION_OPENAI_AUTH_MODE", "api_keys")
    monkeypatch.setenv("VISION_OPENAI_API_KEY", "sk-orchestrator")

    config = load_config(tmp_project_root)

    assert not hasattr(config, "api_key")
    assert not hasattr(config, "api_base_url")

def test_build_provider_uses_orchestrator_shared_api_key_runtime(tmp_project_root, monkeypatch, normalizer_runtime_settings):
    monkeypatch.setenv("VISION_OPENAI_AUTH_MODE", "api_keys")
    monkeypatch.setenv("VISION_OPENAI_API_KEY", "sk-orchestrator")

    provider = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
    )._build_provider()

    assert provider.provider_name == "openai"
    assert provider.api_key == "sk-orchestrator"

def test_build_provider_uses_orchestrator_oauth_runtime(tmp_project_root, monkeypatch, normalizer_runtime_settings):
    monkeypatch.setenv("VISION_OPENAI_AUTH_MODE", "oauth")
    monkeypatch.setenv("VISION_OPENAI_OAUTH_ACCESS_TOKEN", "access-token")
    monkeypatch.setenv("VISION_OPENAI_OAUTH_ACCOUNT_ID", "account-1")

    provider = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
    )._build_provider()

    assert provider.provider_name == "openai_oauth"
