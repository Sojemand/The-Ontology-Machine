from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping

_SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|bearer|token|secret|credential|password)", re.IGNORECASE)


def redact_for_support(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted = {}
        for key, child in value.items():
            key_text = str(key)
            if _SECRET_KEY_RE.search(key_text):
                redacted[key_text] = "[REDACTED]"
            elif key_text in {"raw_provider_response", "output_text"}:
                redacted[key_text] = "[REDACTED_FULL_BODY_AVAILABLE_BY_ARTIFACT_REF]"
            else:
                redacted[key_text] = redact_for_support(child)
        return redacted
    if isinstance(value, list):
        return [redact_for_support(item) for item in value]
    if isinstance(value, str) and _SECRET_KEY_RE.search(value):
        return "[REDACTED]"
    return deepcopy(value)


def redact_capture_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted = {}
        for key, child in value.items():
            key_text = str(key)
            if _SECRET_KEY_RE.search(key_text):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact_capture_payload(child)
        return redacted
    if isinstance(value, list):
        return [redact_capture_payload(item) for item in value]
    if isinstance(value, str) and _SECRET_KEY_RE.search(value):
        return "[REDACTED]"
    return deepcopy(value)
