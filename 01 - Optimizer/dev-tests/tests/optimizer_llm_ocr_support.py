from __future__ import annotations


def _configure(monkeypatch) -> None:
    monkeypatch.setenv("OPTIMIZER_OCR_PROVIDER_ID", "openai")
    monkeypatch.setenv("OPTIMIZER_OCR_PROVIDER_FAMILY", "openai_responses")
    monkeypatch.setenv("OPTIMIZER_OCR_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPTIMIZER_OCR_AUTH_MODE", "api_keys")
    monkeypatch.setenv("OPTIMIZER_OCR_API_KEY", "secret-key")
    monkeypatch.setenv("OPTIMIZER_OCR_MODEL", "gpt-5.4")
    monkeypatch.setenv("OPTIMIZER_OCR_MAX_OUTPUT_TOKENS", "15000")
    monkeypatch.setenv("OPTIMIZER_OCR_TIMEOUT_SECONDS", "120")
