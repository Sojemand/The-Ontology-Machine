"""Soft parsing and repair policy for raw provider JSON text."""
from __future__ import annotations

import json
import math
import re
from typing import Any

from ..providers import ProviderError

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def parse_llm_response(response_text: str) -> dict[str, Any]:
    text = response_text.strip()
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    if not text.startswith("{"):
        brace = text.find("{")
        if brace >= 0:
            text = text[brace:]
    try:
        return _load_object(text)
    except json.JSONDecodeError:
        pass
    sanitized = _close_json(_sanitize_json_text(text))
    try:
        return _load_object(sanitized)
    except json.JSONDecodeError as exc:
        if not text.rstrip().endswith("}") and len(text) > 200:
            raise ProviderError(
                f"JSON abgeschnitten (truncated). max_output_tokens erhoehen. Antwort: {text[:500]}"
            ) from exc
        raise ProviderError(f"JSON-Parse-Fehler. Antwort: {text[:500]}") from exc


def _load_object(text: str) -> dict[str, Any]:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("not an object", text, 0)
    return _sanitize_json_value(parsed)


def _sanitize_json_text(text: str) -> str:
    text = re.sub(r'(:\s*)(\d+),(\d{1,3})(\s*[,}\]\r\n])', r"\1\2.\3\4", text)
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    text = re.sub(r"\bNaN\b|\bInfinity\b|-Infinity\b", "null", text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def _close_json(text: str) -> str:
    stack: list[str] = []
    in_string = False
    escape = False
    for char in text:
        if escape:
            escape = False
        elif char == "\\" and in_string:
            escape = True
        elif char == '"':
            in_string = not in_string
        elif not in_string and char in "{[":
            stack.append("}" if char == "{" else "]")
        elif not in_string and stack and char == stack[-1]:
            stack.pop()
    return text + "".join(reversed(stack))


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_json_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
