from __future__ import annotations

import ingestion_layer_vision.orchestrator_contract as contract

from orchestrator_contract_support import DummyPluginManager
from .orchestrator_extract_document_support import _install_extract_common


def test_extract_document_requires_relative_logical_source_path(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *_args, **_kwargs):
            raise AssertionError("process_single darf bei ungueltigem Request nicht laufen")

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(tmp_path / "out.raw.json"),
            "page_assets_dir": str(tmp_path / "pages"),
            "logical_source_path": r"C:\host\source.txt",
        }
    )
    assert response == {
        "status": "error",
        "error": "logical_source_path muss ein relativer Pfad innerhalb der Pipeline sein.",
    }
    assert manager.calls == []
