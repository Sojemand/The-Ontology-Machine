from __future__ import annotations

from pathlib import Path

from optimizer_ocr import workflow as llm_ocr

from optimizer_llm_ocr_support import _configure


def test_extract_page_assets_rejects_non_json_model_output(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")
    monkeypatch.setattr(llm_ocr, "_post_json", lambda *_args, **_kwargs: {"output_text": "not json"})

    result = llm_ocr.extract_page_assets([str(image_path)])

    assert result["status"] == "error"
    assert "kein valides JSON" in result["errors"][0]


def test_check_readiness_requires_optimizer_ocr_secret(monkeypatch) -> None:
    monkeypatch.setenv("OPTIMIZER_OCR_PROVIDER_ID", "openai")
    monkeypatch.setenv("OPTIMIZER_OCR_PROVIDER_FAMILY", "openai_responses")
    monkeypatch.setenv("OPTIMIZER_OCR_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPTIMIZER_OCR_AUTH_MODE", "api_keys")
    monkeypatch.setenv("OPTIMIZER_OCR_MODEL", "gpt-5.4")
    monkeypatch.delenv("OPTIMIZER_OCR_API_KEY", raising=False)

    ok, detail = llm_ocr.check_readiness()

    assert ok is False
    assert detail == "optimizer_ocr API-Key fehlt."
