"""Text and number coercion helpers for structured/free-text matching."""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime
from typing import Any

_NUMERIC_GROUP_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2019": "'",
    }
)
_NUMERIC_TOKEN_RE = re.compile(r"[-+]?\d(?:[\d., '\u00a0\u202f\u2019]*\d)?")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("ß", "ss").replace("ÃƒÅ¸", "ss").replace("ÃŸ", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_alnum(value: Any) -> str:
    return re.sub(r"[^0-9a-z]+", "", normalize_text(value))


def parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def number_variants(value: int | float) -> set[str]:
    number = float(value)
    if not math.isfinite(number):
        return set()
    base_2 = f"{number:.2f}"
    stripped = base_2.rstrip("0").rstrip(".")
    variants = {base_2, base_2.replace(".", ","), stripped, stripped.replace(".", ",")}
    if abs(number - round(number)) < 1e-9:
        variants.add(str(int(round(number))))
    return {variant for variant in variants if variant}


def _parse_numeric_token(token: str) -> float | None:
    raw = token.strip()
    if not raw:
        return None

    sign = ""
    if raw[:1] in "+-":
        sign, raw = raw[:1], raw[1:]
    if not raw:
        return None

    raw = raw.translate(_NUMERIC_GROUP_TRANSLATION)
    if not re.fullmatch(r"[0-9., ']+", raw):
        return None

    decimal_mark = _detect_decimal_mark(raw)
    if decimal_mark is None:
        normalized = _normalize_integer_part(
            raw,
            extra_group_separators=_integer_group_separators(raw),
        )
    else:
        head, tail = raw.rsplit(decimal_mark, 1)
        if not tail.isdigit():
            return None
        normalized_head = _normalize_integer_part(
            head,
            extra_group_separators=tuple(
                separator
                for separator in (",", ".")
                if separator != decimal_mark and separator in head
            ),
        )
        normalized = None if normalized_head is None else normalized_head + "." + tail
    if normalized is None:
        return None

    try:
        return float(sign + normalized)
    except ValueError:
        return None


def _detect_decimal_mark(raw: str) -> str | None:
    comma_count = raw.count(",")
    dot_count = raw.count(".")
    if comma_count and dot_count:
        return "," if raw.rfind(",") > raw.rfind(".") else "."
    if comma_count > 1 or dot_count > 1:
        return None
    if comma_count == 1:
        return _single_separator_decimal_mark(raw, ",")
    if dot_count == 1:
        return _single_separator_decimal_mark(raw, ".")
    return None


def _single_separator_decimal_mark(raw: str, separator: str) -> str | None:
    head, tail = raw.rsplit(separator, 1)
    if not tail.isdigit():
        return None
    if len(tail) != 3:
        return separator
    if _normalize_integer_part(head, extra_group_separators=(separator,)) is None:
        return separator
    return None


def _integer_group_separators(raw: str) -> tuple[str, ...]:
    separators: list[str] = []
    for separator in (",", "."):
        count = raw.count(separator)
        if count > 1:
            separators.append(separator)
        elif count == 1 and _single_separator_decimal_mark(raw, separator) is None:
            separators.append(separator)
    return tuple(separators)


def _normalize_integer_part(
    raw: str,
    *,
    extra_group_separators: tuple[str, ...] = (),
) -> str | None:
    text = raw.strip()
    if not text:
        return None

    for separator in (" ", "'", *extra_group_separators):
        text = _strip_group_separator(text, separator)
        if text is None:
            return None
    if not text or not text.isdigit():
        return None
    return text


def _strip_group_separator(raw: str, separator: str) -> str | None:
    if separator not in raw:
        return raw
    parts = raw.split(separator)
    if any(not part for part in parts):
        return None
    if not all(part.isdigit() for part in parts):
        return None
    if not 1 <= len(parts[0]) <= 3:
        return None
    if any(len(part) != 3 for part in parts[1:]):
        return None
    return "".join(parts)


def extract_numeric_candidates(text: str) -> list[float]:
    values: list[float] = []
    for candidate in _NUMERIC_TOKEN_RE.findall(text):
        parsed = _parse_numeric_token(candidate)
        if parsed is not None and math.isfinite(parsed):
            values.append(parsed)
    return values
