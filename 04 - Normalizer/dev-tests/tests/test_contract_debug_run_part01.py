from tests.contract_debug_run_shared import *  # noqa: F401,F403

def test_validation_accepts_debug_run_single(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    command = validation.parse_debug_run_command(
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(tmp_path / "session"),
            "output_root": str(tmp_path / "session" / "outputs"),
            "source_path": str(source_path),
            "worker_count": 2,
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        }
    )

    assert command.mode == "single"
    assert command.source_path == source_path
    assert command.worker_count == 2

def test_validation_accepts_debug_run_batch(tmp_path: Path) -> None:
    input_root = tmp_path / "structured"
    input_root.mkdir()

    command = validation.parse_debug_run_command(
        {
            "action": "debug_run",
            "mode": "batch",
            "session_root": str(tmp_path / "session"),
            "output_root": str(tmp_path / "session" / "outputs"),
            "input_root": str(input_root),
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        }
    )

    assert command.mode == "batch"
    assert command.input_root == input_root
    assert command.worker_count is None

def test_validation_rejects_debug_run_missing_runtime_settings(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="runtime_settings fehlt"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
            }
        )

def test_validation_rejects_debug_run_invalid_worker_count(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="worker_count muss eine positive Ganzzahl sein"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "worker_count": 0,
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

def test_validation_rejects_debug_run_unknown_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unbekannte Felder: extra"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
                "extra": True,
            }
        )

def test_validation_rejects_debug_run_source_without_structured_json_suffix(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=r"source_path muss auf \*\.structured\.json enden"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

@pytest.mark.parametrize("dangerous_name", ["config", "runtime", "vendor"])
def test_validation_rejects_debug_run_dangerous_root_names(tmp_path: Path, dangerous_name: str) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="darf nicht auf config/.+Modulroot zeigen"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / dangerous_name),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

def test_validation_rejects_debug_run_module_root_as_output_root(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="output_root darf nicht auf config/.+Modulroot zeigen"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(PROJECT_ROOT),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

@pytest.mark.parametrize("dangerous_name", ["config", "runtime", "vendor"])
def test_validation_rejects_debug_run_under_module_owned_roots(tmp_path: Path, dangerous_name: str) -> None:
    module_root = tmp_path / "04 - Normalizer"
    (module_root / "normalizer_vision").mkdir(parents=True)
    (module_root / "config").mkdir()
    (module_root / "module-manifest.json").write_text("{}", encoding="utf-8")
    source_path = tmp_path / "doc.structured.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="session_root darf nicht auf config/.+Modulroot zeigen"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(module_root / dangerous_name / "debug-session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )
