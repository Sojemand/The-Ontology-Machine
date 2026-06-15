"""Text normalization helpers for source sample inspection."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

WORD_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "because",
    "been",
    "before",
    "between",
    "chapter",
    "could",
    "document",
    "from",
    "have",
    "into",
    "more",
    "page",
    "said",
    "shall",
    "story",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "und",
    "werden",
    "were",
    "when",
    "where",
    "which",
    "with",
    "would",
}


def excerpt_chunks(text: str, *, max_chars: int) -> tuple[list[str], bool]:
    compact = re.sub(r"\n{3,}", "\n\n", str(text or "").strip())
    if not compact:
        return [], False
    truncated = len(compact) > max_chars
    clipped = compact[:max_chars].rstrip()
    chunks: list[str] = []
    while clipped:
        chunk = clipped[:2000].rstrip()
        chunks.append(chunk)
        clipped = clipped[len(chunk) :].lstrip()
    return chunks, truncated


def keyword_markers(text: str, *, limit: int) -> list[str]:
    counter: Counter[str] = Counter()
    for token in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text.lower()):
        cleaned = token.strip("-'")
        if cleaned and cleaned not in WORD_STOPWORDS:
            counter[cleaned] += 1
    return [word for word, _count in counter.most_common(limit)]


def append_label_value(items: list[str], key: Any, value: Any) -> None:
    key_text = str(key or "").strip()
    value_text = stringify_short(value)
    if key_text and value_text:
        items.append(f"{key_text}: {value_text}")
    elif key_text:
        items.append(key_text)


def append_text(items: list[str], value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            append_text(items, item)
        return
    if isinstance(value, dict):
        for key in ("text", "value", "content", "summary", "label", "title", "heading", "excerpt"):
            if key in value:
                append_text(items, value.get(key))
        return
    text = str(value or "").strip()
    if text:
        items.append(text)


def stringify_short(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:240]


def join_unique(parts) -> str:
    seen: set[str] = set()
    values: list[str] = []
    for part in parts:
        text = re.sub(r"[ \t]+", " ", str(part or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        values.append(text)
    return "\n\n".join(values)


def limit_unique(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text[:240])
        if len(result) >= limit:
            break
    return result


def flatten(groups) -> list[str]:
    values: list[str] = []
    for group in groups:
        values.extend(list(group))
    return values
