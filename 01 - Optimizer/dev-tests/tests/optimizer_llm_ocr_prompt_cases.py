from __future__ import annotations

import json
from pathlib import Path

from optimizer_ocr import workflow as llm_ocr

from optimizer_llm_ocr_support import _configure


def test_extract_page_assets_uses_owner_prompt_template(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")
    prompt_path = tmp_path / "optimizer_ocr_prompt.md"
    prompt_path.write_text("OCR custom prompt for {page_count} pages. {source_filename_sentence}", encoding="utf-8")
    monkeypatch.setenv("OPTIMIZER_OCR_PROMPT_PATH", str(prompt_path))
    calls: list[dict[str, object]] = []

    def _post_json(settings, path, payload):
        del settings, path
        calls.append(payload)
        return {"output_text": json.dumps({"blocks": [], "metadata": {}})}

    monkeypatch.setattr(llm_ocr, "_post_json", _post_json)

    result = llm_ocr.extract_page_assets([str(image_path)], source_path=tmp_path / "scan.png")

    assert result["status"] == "success"
    content = calls[0]["input"][0]["content"][0]
    assert content["text"] == "OCR custom prompt for 1 pages. Source filename: scan.png."
