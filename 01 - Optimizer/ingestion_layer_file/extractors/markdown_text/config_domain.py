"""Config-style text parsing for the built-in text extractor."""
from __future__ import annotations

import re

from .block_domain import make_header_block, make_text_block
from .types import ParseOutcome

_SECTION_RE = re.compile(r"^\[(.+)\]\s*$")
_SECTION_EXTS = {".ini", ".toml", ".cfg", ".conf"}


def parse_config(lines: list[str], ext: str) -> ParseOutcome:
    outcome = ParseOutcome()
    current_lines: list[str] = []
    current_section: str | None = None

    def flush_section() -> None:
        if not current_lines:
            return
        text = "\n".join(current_lines).strip()
        current_lines.clear()
        if not text:
            return
        block_type = "config_section" if current_section else "paragraph"
        block_id = f"section_{outcome.metrics.paragraph_count}" if current_section else f"para_{outcome.metrics.paragraph_count}"
        outcome.blocks.append(make_text_block(block_id, block_type, outcome.metrics.paragraph_count, text))
        outcome.metrics.paragraph_count += 1

    for line in lines:
        match = _SECTION_RE.match(line)
        if match and ext in _SECTION_EXTS:
            flush_section()
            current_section = match.group(1)
            outcome.blocks.append(
                make_header_block(
                    f"heading_{outcome.metrics.heading_count}",
                    outcome.metrics.paragraph_count,
                    current_section,
                    2,
                )
            )
            outcome.metrics.heading_count += 1
            outcome.metrics.headings.append(current_section)
            outcome.metrics.paragraph_count += 1
            continue
        if not line.strip():
            flush_section()
            current_section = None
            continue
        current_lines.append(line)

    flush_section()
    return outcome
