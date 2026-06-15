from __future__ import annotations

import json
from pathlib import Path

from optimizer_ocr import workflow as llm_ocr

from optimizer_llm_ocr_support import _configure


def test_extract_page_assets_normalizes_strict_llm_json(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")
    calls: list[dict[str, object]] = []

    def _post_json(settings, path, payload):
        calls.append({"settings": settings, "path": path, "payload": payload})
        return {
            "output_text": json.dumps(
                {
                    "blocks": [
                        {
                            "id": "b1",
                            "type": "paragraph",
                            "layout_label": "body",
                            "position": {"page": 1, "row": None, "col": None},
                            "value": "Hallo Welt",
                            "value_type": "text",
                            "formatting": {},
                            "confidence": 0.98765,
                        }
                    ],
                    "metadata": {"model_note": "ok"},
                }
            )
        }

    monkeypatch.setattr(llm_ocr, "_post_json", _post_json)

    result = llm_ocr.extract_page_assets([str(image_path)], source_path=tmp_path / "scan.png")

    assert result["status"] == "success"
    assert result["blocks"][0]["value"] == "Hallo Welt"
    assert result["blocks"][0]["confidence"] == 0.9877
    assert result["metadata"]["ocr_engine"] == "llm"
    assert result["metadata"]["ocr_provider_id"] == "openai"
    assert "secret-key" not in json.dumps(result, ensure_ascii=False)
    assert calls[0]["path"] == "/responses"


def test_extract_page_assets_accepts_minimal_block_shape(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")

    monkeypatch.setattr(
        llm_ocr,
        "_post_json",
        lambda *_args, **_kwargs: {
            "output_text": json.dumps(
                {
                    "blocks": [
                        {"id": "b1", "type": "paragraph", "value": "Plain", "formatting": {"bold": False}},
                        {"id": "b2", "type": "heading", "value": "Bold", "bold": True, "page": 2},
                    ],
                    "metadata": {},
                }
            )
        },
    )

    result = llm_ocr.extract_page_assets([str(image_path)])

    assert result["status"] == "success"
    assert result["blocks"] == [
        {"id": "b1", "type": "paragraph", "value": "Plain"},
        {"id": "b2", "type": "heading", "value": "Bold", "position": {"page": 2}, "formatting": {"bold": True}},
    ]
