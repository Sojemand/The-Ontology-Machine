from __future__ import annotations

import pytest

from runtime_build_tooling_support import PIPELINE_ROOT, TOOLS_ROOT, load_tool_module


def test_all_in_one_installer_stages_clean_uninstall_surface() -> None:
    module = load_tool_module("test_all_in_one_uninstall_surface", TOOLS_ROOT / "build-all-in-one-installer.py")

    batch = module._uninstall_launcher_batch()
    script = module._uninstall_powershell()
    readme = module._root_readme()

    assert "Uninstall Ontology Machine.ps1" in batch
    assert "start \"Ontology Machine Uninstaller\"" in batch
    assert 'for %%I in ("%~dp0.") do set "ROOT=%%~fI"' in batch
    assert r'set "SCRIPT=%ROOT%\Uninstall Ontology Machine.ps1"' in batch
    assert "release-manifest.json" in script
    assert ".Trim().Trim([char[]]@('\"', \"'\"))" in script
    assert "Type DELETE to continue" in script
    assert "post-uninstall residual cleanup" in script
    assert "unknown top-level item(s)" in script
    assert "Enterprise Stack" in script
    assert "Client Frontend" in script
    assert "Desktop\\Ontology Machine" in script
    assert "Remove-UninstallRegistryEntries" in script
    assert "Uninstall Ontology Machine.bat" in readme


def test_all_in_one_installer_ships_sampledb_without_post_install_seed() -> None:
    module = load_tool_module("test_all_in_one_sampledb_no_seed", TOOLS_ROOT / "build-all-in-one-installer.py")
    inno_script = (PIPELINE_ROOT / "installer" / "OntologyMachineAllInOne.iss").read_text(encoding="utf-8")
    readme = module._root_readme()

    assert module.ROOT_PAYLOAD_DIRS == ("SampleDB", "Extractor_Tools", "The Machine Doku PDF")
    assert module.DEFAULT_DEMO_DB_PATH == r"SampleDB\Consciousness Travel - Default Demo\Corpus\corpus.db"
    assert (PIPELINE_ROOT / "The Machine Doku PDF" / "Quickstart_Handbook.pdf").is_file()
    assert "Apply Default Demo State" not in inno_script
    assert 'Name: "desktop_shortcuts"; Description: "Desktop-Ordner mit Ontology Machine Verknuepfungen"' in inno_script
    assert 'Name: "desktop_shortcuts"; Description: "Desktop-Ordner mit Ontology Machine Verknuepfungen"; Flags: unchecked' not in inno_script
    assert "The Machine Doku PDF\\Quickstart_Handbook.pdf" in inno_script
    assert 'DestDir: "{autodesktop}\\{#MyAppName}"' in inno_script
    assert "Post-install defaults" not in readme
    assert "Orchestrator state is not seeded by the installer" in readme
    assert "SampleDB\\Consciousness Travel - Default Demo\\Corpus\\corpus.db" in readme
    assert "Start Article Archive Extractor.bat" in readme
    assert "Start YouTube Transcript Extractor.bat" in readme
    assert "Start Audio Transcription Extractor.bat" in readme
    assert "Extractor_Tools contains small local sidecars" in readme
    assert "Quickstart Handbook PDF" in readme


def test_all_in_one_inno_uninstall_removes_install_root_without_residual_prompt() -> None:
    inno_script = (PIPELINE_ROOT / "installer" / "OntologyMachineAllInOne.iss").read_text(encoding="utf-8")

    assert "procedure DeleteMutableData();" in inno_script
    assert "procedure DeleteInstallRoot();" in inno_script
    assert "DeleteMutableData();" in inno_script
    assert "DeleteInstallRoot();" in inno_script
    assert "MsgBox(" not in inno_script
    assert "DeleteEmptyInstallShells" not in inno_script
    assert "RemoveIfEmpty" not in inno_script
    assert "uninsneveruninstall" not in inno_script


def test_all_in_one_root_payload_skips_idle_sqlite_sidecars(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_all_in_one_stage_sidecars", TOOLS_ROOT / "all_in_one_stage.py")
    source = tmp_path / "root" / "SampleDB" / "Demo" / "Corpus"
    source.mkdir(parents=True)
    (source / "corpus.db").write_text("db", encoding="utf-8")
    (source / "corpus.db-wal").write_text("", encoding="utf-8")
    (source / "corpus.db-shm").write_text("shm", encoding="utf-8")
    monkeypatch.setattr(module, "PIPELINE_ROOT", tmp_path / "root")
    monkeypatch.setattr(module, "ROOT_PAYLOAD_DIRS", ("SampleDB",))

    module.stage_root_payloads(tmp_path / "stage")

    target = tmp_path / "stage" / "SampleDB" / "Demo" / "Corpus"
    assert (target / "corpus.db").read_text(encoding="utf-8") == "db"
    assert not (target / "corpus.db-wal").exists()
    assert not (target / "corpus.db-shm").exists()


def test_all_in_one_root_payload_skips_python_local_debris(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_all_in_one_stage_python_debris", TOOLS_ROOT / "all_in_one_stage.py")
    source = tmp_path / "root" / "Extractor_Tools" / "Article Archive Extractor"
    source.mkdir(parents=True)
    (source / "article_archive_extractor.py").write_text("print('ok')", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "tool.cpython-311.pyc").write_bytes(b"cache")
    (source / ".venv" / "Scripts").mkdir(parents=True)
    (source / ".venv" / "Scripts" / "python.exe").write_bytes(b"venv")
    monkeypatch.setattr(module, "PIPELINE_ROOT", tmp_path / "root")
    monkeypatch.setattr(module, "ROOT_PAYLOAD_DIRS", ("Extractor_Tools",))

    module.stage_root_payloads(tmp_path / "stage")

    target = tmp_path / "stage" / "Extractor_Tools" / "Article Archive Extractor"
    assert (target / "article_archive_extractor.py").exists()
    assert not (target / "__pycache__").exists()
    assert not (target / ".venv").exists()


def test_all_in_one_root_payload_rejects_non_empty_sqlite_wal(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_all_in_one_stage_non_empty_wal", TOOLS_ROOT / "all_in_one_stage.py")
    source = tmp_path / "root" / "SampleDB" / "Demo" / "Corpus"
    source.mkdir(parents=True)
    (source / "corpus.db").write_text("db", encoding="utf-8")
    (source / "corpus.db-wal").write_text("pending", encoding="utf-8")
    monkeypatch.setattr(module, "PIPELINE_ROOT", tmp_path / "root")
    monkeypatch.setattr(module, "ROOT_PAYLOAD_DIRS", ("SampleDB",))
    existing = tmp_path / "stage" / "SampleDB" / "existing.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeError, match="non-empty SQLite WAL sidecar"):
        module.stage_root_payloads(tmp_path / "stage")
    assert existing.read_text(encoding="utf-8") == "keep"


def test_run_dev_tests_preferred_order_keeps_interpreter_before_validator() -> None:
    module = load_tool_module("test_run_dev_tests_order", TOOLS_ROOT / "run-dev-tests.py")

    assert "01 - Optimizer" in module.PREFERRED_ORDER
    assert "02 - Interpreter" in module.PREFERRED_ORDER
    assert module.PREFERRED_ORDER.index("02 - Interpreter") < module.PREFERRED_ORDER.index("03 - Validator")


def test_run_dev_tests_warns_about_legacy_root_venv(tmp_path, capsys) -> None:
    module = load_tool_module("test_run_dev_tests", TOOLS_ROOT / "run-dev-tests.py")

    suite_dir = tmp_path / "module" / "dev-tests"
    suite_dir.mkdir(parents=True)
    (suite_dir.parent / ".venv").mkdir()
    suite = module.Suite(
        name="demo",
        display_name="Demo",
        kind="python",
        suite_dir=suite_dir,
        bootstrap_script=suite_dir / "bootstrap.bat",
        run_script=suite_dir / "run-tests.bat",
        aliases=(),
    )

    module._warn_if_legacy_root_venv_exists(suite)

    captured = capsys.readouterr()
    assert "Ignoriere Altlast-venv ausserhalb der Suite" in captured.err
    assert str(suite_dir.parent / ".venv") in captured.err
