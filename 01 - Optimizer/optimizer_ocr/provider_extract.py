from __future__ import annotations

from typing import Any

from .errors import LlmOcrResponseError


def extract_responses_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") in {"output_text", "text"} and block.get("text"):
                return str(block["text"])
    raise LlmOcrResponseError("LLM-OCR Provider lieferte keinen Text-Output.")


def extract_chat_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmOcrResponseError("LLM-OCR Chat Provider lieferte keine Antwortauswahl.")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        text = "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        if text.strip():
            return text
    raise LlmOcrResponseError("LLM-OCR Chat Provider lieferte keinen Text-Output.")
