from tests.normalizer_workflow_shared import *  # noqa: F401,F403

def test_normalize_single_file(tmp_project_root, sample_structured_file, mock_provider, normalizer_runtime_settings):
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=mock_provider,
    )
    normalized_output_path = tmp_project_root / "output" / "sample.pdf.structured.normalized.json"
    result = normalizer.normalize(sample_structured_file, normalized_output_path)

    assert result.status == "OK"
    assert result.output_path == str(normalized_output_path)
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["classification"]["document_type"] == "utility_cost_statement"
    assert output_data["context"]["taxonomy_profile_id"] == "housing.default.v1"
    assert output_data["projection"]["selection"]["mode"] == "fallback"
    assert output_data["content"]["rows"][0]["_units"] == {
        "building_total_heating_cost": "EUR",
        "tenant_share_heating_cost": "EUR",
    }

def test_normalize_batch(tmp_project_root, sample_batch_dir, mock_provider, normalizer_runtime_settings):
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=mock_provider,
    )
    output_root = tmp_project_root / "normalized_root"
    results = normalizer.normalize_batch(sample_batch_dir, output_root, workers=2)

    assert len(results) == 2
    assert all(result.status == "OK" for result in results)
    assert {Path(result.output_path) for result in results} == {
        output_root / "normalized" / "sample_0.pdf.structured.normalized.json",
        output_root / "normalized" / "sample_1.pdf.structured.normalized.json",
    }

def test_normalize_batch_uses_sequential_fallback_and_progress_callback_with_injected_provider(
    tmp_project_root,
    sample_batch_dir,
    mock_provider,
    normalizer_runtime_settings,
    monkeypatch,
):
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=mock_provider,
    )
    progress_paths: list[str] = []

    monkeypatch.setattr(
        "normalizer_vision.normalizer.ThreadPoolExecutor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("ThreadPoolExecutor should not be used")),
    )

    results = normalizer.normalize_batch(
        sample_batch_dir,
        tmp_project_root / "normalized_root",
        workers=4,
        progress_callback=lambda result: progress_paths.append(Path(result.input_path).name),
    )

    expected_names = sorted(path.name for path in sample_batch_dir.glob("*.structured.json"))
    assert [Path(result.input_path).name for result in results] == expected_names
    assert progress_paths == expected_names

def test_normalize_retries_transient_provider_error(
    tmp_project_root,
    sample_structured_file,
    sample_model_output,
    normalizer_runtime_settings,
    monkeypatch,
):
    class FlakyProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            self.calls += 1
            if self.calls == 1:
                raise ProviderError("OpenAI nicht erreichbar: connection aborted")
            return json.dumps(sample_model_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    monkeypatch.setattr("normalizer_vision.normalizer.time.sleep", lambda _seconds: None)
    provider = FlakyProvider()
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=provider,
    )

    result = normalizer.normalize(sample_structured_file, tmp_project_root / "output" / "sample.pdf.structured.normalized.json")
    assert result.status == "OK"
    assert provider.calls == 2

def test_normalize_does_not_retry_non_retriable_provider_error(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    class AuthFailProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            self.calls += 1
            raise ProviderError("OpenAI API Fehler 401: unauthorized", status_code=401)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    provider = AuthFailProvider()
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=provider,
    )

    result = normalizer.normalize(sample_structured_file, tmp_project_root / "output" / "sample.pdf.structured.normalized.json")
    assert result.status == "ERROR"
    assert "401" in result.message
    assert provider.calls == 1

def test_parse_model_output_accepts_json_code_fences():
    parsed = DocumentNormalizer._parse_model_output(
        """```json\n{\"schema_version\":\"1.0\",\"processing\":{},\"classification\":{},\"context\":{},\"content\":{}}\n```"""
    )
    assert parsed == {"schema_version": "1.0", "processing": {}, "classification": {}, "context": {}, "content": {}}

def test_normalize_reports_error_for_non_object_model_output(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    class NonObjectProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return '["not", "an", "object"]'

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=NonObjectProvider(),
    )
    result = normalizer.normalize(sample_structured_file, tmp_project_root / "output" / "sample.pdf.structured.normalized.json")

    assert result.status == "ERROR"
    assert "JSON-Objekt" in result.message
