from __future__ import annotations

import re
import unicodedata

from .numeric_claim_patterns import (
    ADDRESS_RE,
    CLAIM_TEXT_TRANSLATION,
    CURRENCY_OR_UNIT_RE,
    DECIMAL_RE,
    IDENTIFIER_RE,
    LABEL_SUFFIX_BEFORE_NUMBER_RE,
    LAYOUT_CONTROL_CHARS,
    OCR_DIGIT_TRANSLATION,
    POSTAL_CODE_RE,
    QUANTITY_RE,
    VALUE_UNIT_AFTER_NUMBER_RE,
    ZERO_WIDTH_CHARS,
)


def prepare_claim_text(value: str) -> tuple[str, set[str]]:
    text = str(value or "").translate(CLAIM_TEXT_TRANSLATION)
    flags: set[str] = set()
    chars: list[str] = []
    control_count = 0
    replacement_count = 0
    format_count = 0
    for index, char in enumerate(text):
        if char in LAYOUT_CONTROL_CHARS:
            chars.append(" ")
            continue
        if char in ZERO_WIDTH_CHARS:
            format_count += 1
            continue
        if char == "\ufffd":
            replacement_count += 1
            chars.append(" ")
            continue
        if unicodedata.category(char).startswith("C"):
            control_count += 1
            if _is_between_digitish(text, index):
                continue
            chars.append(" ")
            continue
        chars.append(char)
    _add_quality_flags(flags, control_count=control_count, replacement_count=replacement_count, format_count=format_count)
    return "".join(chars), flags


def strength_for_quality(default: str, quality_flags: set[str] | frozenset[str]) -> str:
    return "weak" if "dirty_text" in quality_flags else default


def strength_for_number(
    *,
    text: str,
    start: int,
    end: int,
    display_value: str,
    parsed_number: float,
    context_hint: str,
    quality_flags: set[str],
) -> str:
    if "dirty_text" in quality_flags:
        return "weak"
    token = display_value.strip()
    if _is_single_digit_label_suffix(text=text, start=start, end=end, token=token):
        quality_flags.add("label_suffix")
        return "weak"
    window = f"{text[max(0, start - 24):start]} {token} {text[end:end + 24]}"
    context = f"{context_hint} {window}"
    if CURRENCY_OR_UNIT_RE.search(context) or DECIMAL_RE.search(token):
        return "strong"
    if QUANTITY_RE.search(context):
        return "strong"
    if ADDRESS_RE.search(context) or POSTAL_CODE_RE.fullmatch(token):
        return "medium"
    if IDENTIFIER_RE.search(context):
        return "medium"
    if abs(parsed_number) >= 1000:
        return "medium"
    return "medium"


def _add_quality_flags(flags: set[str], *, control_count: int, replacement_count: int, format_count: int) -> None:
    if control_count:
        flags.add("control_chars")
    if replacement_count:
        flags.add("replacement_chars")
    if format_count:
        flags.add("format_chars")
    if control_count + replacement_count:
        flags.add("dirty_text")


def _is_between_digitish(text: str, index: int) -> bool:
    left = text[index - 1] if index > 0 else ""
    right = text[index + 1] if index + 1 < len(text) else ""
    return left.isdigit() and right.isdigit()


def _is_single_digit_label_suffix(*, text: str, start: int, end: int, token: str) -> bool:
    normalized_token = token.translate(OCR_DIGIT_TRANSLATION)
    if not re.fullmatch(r"\d", normalized_token):
        return False
    if VALUE_UNIT_AFTER_NUMBER_RE.match(text[end:]):
        return False
    prefix = text[max(0, start - 24):start]
    return bool(LABEL_SUFFIX_BEFORE_NUMBER_RE.search(prefix))
