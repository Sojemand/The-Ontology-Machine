from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import ingestion_layer_vision.orchestrator_contract as contract
import ingestion_layer_file.orchestrator_contract as file_contract
from orchestrator_contract_support import DummyPluginManager, debug_single_processor


def test_debug_run_single_writes_outputs_below_session_root(tmp_path, monkeypatch) -> None:
    source = tmp_path / "input" / "docs" / "invoice.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("pdf", encoding="utf-8")
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    _install_common(monkeypatch, tmp_path, manager, debug_single_processor(captured, capture_init_kwargs=True))

    response = contract._debug_run(
        {
            "session_root": str(session_root),
            "input_root": str(source.parent.parent),
            "output_root": str(output_root),
            "mode": "single",
            "source_path": str(source),
            "logical_source_path": "docs/invoice.pdf",
            "filters": {},
            "worker_count": 3,
            "hash_tools": {"use_processed_hashes": False},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))

    assert response["status"] == "ok"
    assert response["outputs"] == {
        "raw_extracts": ["outputs/raw_extracts/docs/invoice.raw.json"],
        "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
    }
    assert captured["config"].parallel_workers == 3
    assert "output_dir" not in captured["init_kwargs"]
    assert captured["kwargs"]["logical_source_path"] == "docs/invoice.pdf"
    assert snapshot["status"] == "ok"
    assert snapshot["counters"] == {"raw_extracts_written": 1, "page_assets_written": 1}
    assert manager.calls == ["kill_all"]


def test_debug_run_single_ignores_stale_missing_input_root(tmp_path, monkeypatch) -> None:
    source = tmp_path / "storage" / "scan.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("pdf", encoding="utf-8")
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    _install_common(monkeypatch, tmp_path, manager, debug_single_processor(captured))

    response = contract._debug_run(
        {
            "session_root": str(session_root),
            "input_root": str(tmp_path / "Artefacts Test 03" / "Input"),
            "output_root": str(output_root),
            "mode": "single",
            "source_path": str(source),
            "filters": {},
            "worker_count": 1,
            "hash_tools": {"use_processed_hashes": False},
        }
    )

    assert response["status"] == "ok"
    assert captured["source_path"] == source
    assert captured["kwargs"]["logical_source_path"] == "scan.pdf"
    assert manager.calls == ["kill_all"]


def test_file_debug_run_single_accepts_source_outside_input_root(tmp_path, monkeypatch) -> None:
    input_root = tmp_path / "input"
    outside_root = tmp_path / "outside"
    input_root.mkdir()
    outside_root.mkdir()
    source = outside_root / "Apparatetausch.docx"
    source.write_text("docx", encoding="utf-8")
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    _install_common(monkeypatch, tmp_path, manager, debug_single_processor(captured), contract_module=file_contract)

    response = file_contract._debug_run(
        {
            "session_root": str(session_root),
            "input_root": str(input_root),
            "output_root": str(output_root),
            "mode": "single",
            "source_path": str(source),
            "filters": {},
            "worker_count": 1,
            "hash_tools": {"use_processed_hashes": False},
        }
    )

    assert response["status"] == "ok"
    assert response["outputs"]["page_assets"] == ["outputs/page_assets/Apparatetausch/page_001.png"]
    assert captured["source_path"] == source
    assert captured["kwargs"]["logical_source_path"] == "Apparatetausch.docx"
    assert manager.calls == ["kill_all"]


def test_file_debug_run_single_budgets_long_explicit_output_targets(tmp_path, monkeypatch) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    source = input_root / "sample.pdf"
    source.write_text("pdf", encoding="utf-8")
    session_root = _deep_session_root(tmp_path)
    output_root = session_root / "outputs"
    long_name = (
        "201611136 V - Reinhard Feinmechanik Dietzenbach - "
        + ("Bestellung Tieflochbohrungen " * 2)
    ).strip() + ".pdf"
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    _install_common(monkeypatch, tmp_path, manager, debug_single_processor(captured), contract_module=file_contract)

    response = file_contract._debug_run(
        {
            "session_root": str(session_root),
            "input_root": str(input_root),
            "output_root": str(output_root),
            "mode": "single",
            "source_path": str(source),
            "logical_source_path": long_name,
            "filters": {},
            "worker_count": 1,
            "hash_tools": {"use_processed_hashes": False},
        }
    )

    raw_output_path = Path(captured["kwargs"]["raw_output_path"])
    page_assets_dir = Path(captured["kwargs"]["page_assets_dir"])

    assert response["status"] == "ok"
    assert len(str(raw_output_path)) <= 259
    assert len(str(page_assets_dir / "page_001.png")) <= 259
    assert raw_output_path.name.endswith(".raw.json")
    assert long_name not in raw_output_path.name
    assert long_name.removesuffix(".pdf") not in page_assets_dir.name


def _install_common(
    monkeypatch,
    tmp_path: Path,
    manager: DummyPluginManager,
    processor_cls,
    *,
    contract_module=contract,
) -> None:
    monkeypatch.setattr(contract_module, "APP_HOME", tmp_path / "app-home")
    monkeypatch.setattr(contract_module, "load_config", lambda _path: SimpleNamespace(parallel_workers=0))
    monkeypatch.setattr(contract_module, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(contract_module, "Processor", processor_cls)


def _deep_session_root(tmp_path: Path) -> Path:
    root = tmp_path / "session"
    index = 0
    while len(str(root / "outputs" / "page_assets")) < 170:
        root = root / f"deep_segment_{index:02d}"
        index += 1
    return root
