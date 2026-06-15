from __future__ import annotations

from types import SimpleNamespace

from ingestion_layer_vision.processor import Processor

from processor_security_env import VALID_HASH, make_processor


def test_write_extract_o_creat_prevents_overwrite(tmp_path, monkeypatch):
    proc = make_processor(tmp_path)

    extracts_dir = tmp_path / "raw_extracts"
    extracts_dir.mkdir(parents=True)
    source = SimpleNamespace(
        content_hash=VALID_HASH,
        relative_path="report.pdf",
        filename="report.pdf",
    )
    extract = SimpleNamespace(
        source=source,
        page_number=None,
    )

    slug = Processor._build_output_slug("report.pdf", VALID_HASH)
    first_candidate = extracts_dir / f"{slug}.raw.json"
    first_candidate.write_text('{"existing": true}', encoding="utf-8")

    monkeypatch.setattr(
        "ingestion_layer_vision.processor.raw_extract_to_dict",
        lambda ex: {"test": True},
    )
    monkeypatch.setattr(
        "ingestion_layer_vision.processor.atomic_json_write",
        lambda path, data: path.write_text('{"test": true}', encoding="utf-8"),
    )

    result_path = proc._write_extract(extract, extracts_dir)

    assert result_path != first_candidate
    assert result_path.exists()
    assert result_path.name.endswith(".raw.json")
    assert first_candidate.read_text(encoding="utf-8") == '{"existing": true}'
