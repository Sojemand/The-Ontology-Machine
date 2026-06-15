from __future__ import annotations

import re

from ..models.coercion import _parse_numeric_token
from .numeric_claim_patterns import NUMBER_WITH_OPTIONAL_CURRENCY_RE, OCR_DIGIT_TRANSLATION


def parse_native_number(text: str) -> float | None:
    match = NUMBER_WITH_OPTIONAL_CURRENCY_RE.fullmatch(text)
    if match is None:
        return None
    parsed, _flags = parse_claim_number(match.group("number"))
    return parsed


def parse_claim_number(token: str) -> tuple[float | None, set[str]]:
    if not re.search(r"\d", str(token or "")):
        return None, set()
    normalized = str(token or "").translate(OCR_DIGIT_TRANSLATION)
    flags: set[str] = set()
    if normalized != str(token or ""):
        flags.add("ocr_digit_substitution")
    return _parse_numeric_token(normalized), flags
