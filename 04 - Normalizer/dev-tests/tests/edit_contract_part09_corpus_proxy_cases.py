from tests.edit_contract_shared import *  # noqa: F401,F403


def test_corpus_proxy_normalizes_builder_detail_envelope() -> None:
    payload = corpus_proxy._normalize_contract_response(
        {
            "status": "ok",
            "headline": "New corpus DB created and release activated",
            "detail": {
                "corpus_db_path": "C:/Artefacts/Corpus/semantic-release-default-2026-04-05-corpus-en.db",
                "previous_default_corpus_db_path": "C:/Artefacts/Corpus/corpus.db",
                "taxonomy_locale": "en",
            },
        }
    )

    assert payload["status"] == "ok"
    assert payload["corpus_db_path"].endswith("semantic-release-default-2026-04-05-corpus-en.db")
    assert payload["previous_default_corpus_db_path"].endswith("Corpus/corpus.db")
    assert payload["headline"] == "New corpus DB created and release activated"


def test_corpus_proxy_invocation_writes_request_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_root = tmp_path / "05 - Corpus Builder"
    module_root.mkdir()
    captured: dict[str, object] = {}

    def fake_atomic_json_write(path: Path, payload: dict) -> None:
        captured["request_path"] = path
        captured["payload"] = payload
        path.write_text(json.dumps(payload), encoding="utf-8")

    def fake_run(args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        response_path = Path(args[args.index("--response") + 1])
        response_path.write_text(json.dumps({"status": "ok", "detail": {"done": True}}), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.delenv("NORMALIZER_CORPUS_BUILDER_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(corpus_proxy, "atomic_json_write", fake_atomic_json_write)
    monkeypatch.setattr(corpus_proxy, "_contract_python", lambda root: tmp_path / "python.exe")
    monkeypatch.setattr(corpus_proxy.subprocess, "run", fake_run)

    result = corpus_proxy._invoke_contract(module_root, {"action": "activate_semantic_release"})

    assert result["done"] is True
    assert captured["payload"] == {"action": "activate_semantic_release"}
    assert Path(captured["request_path"]).name == "request.json"
    assert captured["timeout"] == 1800.0


def test_corpus_proxy_invocation_fails_closed_on_contract_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_root = tmp_path / "05 - Corpus Builder"
    module_root.mkdir()

    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setenv("NORMALIZER_CORPUS_BUILDER_TIMEOUT_SECONDS", "0.25")
    monkeypatch.setattr(corpus_proxy, "_contract_python", lambda root: tmp_path / "python.exe")
    monkeypatch.setattr(corpus_proxy.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Corpus-Builder-Contract Timeout nach 0.25s"):
        corpus_proxy._invoke_contract(module_root, {"action": "activate_semantic_release"})


def test_corpus_proxy_contract_result_fails_closed_without_response(tmp_path: Path) -> None:
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(RuntimeError, match="keine response.json"):
        corpus_proxy._handle_contract_result(completed, tmp_path / "response.json")


def test_corpus_proxy_contract_result_rejects_invalid_response_json(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    response_path.write_text("{broken", encoding="utf-8")
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(RuntimeError, match="ungueltige response.json"):
        corpus_proxy._handle_contract_result(completed, response_path)


def test_corpus_proxy_contract_python_fails_closed_without_builder_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_root = tmp_path / "05 - Corpus Builder"
    module_root.mkdir()
    monkeypatch.delenv("NORMALIZER_CORPUS_BUILDER_PYTHON", raising=False)

    with pytest.raises(ValueError, match="Corpus-Builder-Runtime fehlt"):
        corpus_proxy._contract_python(module_root)


def test_corpus_proxy_contract_python_rejects_missing_explicit_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_python = tmp_path / "missing-python.exe"
    monkeypatch.setenv("NORMALIZER_CORPUS_BUILDER_PYTHON", str(missing_python))

    with pytest.raises(ValueError, match="zeigt auf keine Datei"):
        corpus_proxy._contract_python(tmp_path)
