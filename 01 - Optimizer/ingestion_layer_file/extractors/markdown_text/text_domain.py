"""Plaintext paragraph parsing for the built-in text extractor."""
from __future__ import annotations

import re

from .block_domain import make_text_block
from .types import ParseOutcome


def parse_plaintext(text: str) -> ParseOutcome:
    outcome = ParseOutcome()
    for paragraph in re.split(r"\n\s*\n", text):
        cleaned = paragraph.strip()
        if not cleaned:
            continue
        outcome.blocks.append(
            make_text_block(
                f"para_{outcome.metrics.paragraph_count}",
                "paragraph",
                outcome.metrics.paragraph_count,
                cleaned,
            )
        )
        outcome.metrics.paragraph_count += 1
    return outcome
