"""Markdown-specific parsing for the built-in text extractor."""
from __future__ import annotations

import re

from .block_domain import make_header_block, make_text_block
from .types import ParseOutcome

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_CODE_FENCE_RE = re.compile(r"^```")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.+)$")


def parse_markdown(lines: list[str]) -> ParseOutcome:
    outcome = ParseOutcome()
    in_code_block = False
    code_lines: list[str] = []
    paragraph_lines: list[str] = []
    block_idx = 0

    def flush_paragraph() -> None:
        nonlocal block_idx
        if not paragraph_lines:
            return
        text = "\n".join(paragraph_lines).strip()
        paragraph_lines.clear()
        if not text:
            return
        outcome.blocks.append(
            make_text_block(
                f"para_{outcome.metrics.paragraph_count}",
                "paragraph",
                block_idx,
                text,
            )
        )
        outcome.metrics.paragraph_count += 1
        block_idx += 1

    for line in lines:
        if _CODE_FENCE_RE.match(line):
            if in_code_block:
                outcome.blocks.append(
                    make_text_block(
                        f"code_{outcome.metrics.code_block_count}",
                        "code_block",
                        block_idx,
                        "\n".join(code_lines),
                    )
                )
                outcome.metrics.code_block_count += 1
                block_idx += 1
                code_lines.clear()
                in_code_block = False
            else:
                flush_paragraph()
                in_code_block = True
            continue
        if in_code_block:
            code_lines.append(line)
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush_paragraph()
            text = heading_match.group(2).strip()
            outcome.metrics.headings.append(text)
            outcome.blocks.append(
                make_header_block(
                    f"heading_{outcome.metrics.heading_count}",
                    block_idx,
                    text,
                    len(heading_match.group(1)),
                )
            )
            outcome.metrics.heading_count += 1
            block_idx += 1
            continue

        list_match = _LIST_RE.match(line)
        if list_match:
            flush_paragraph()
            outcome.blocks.append(
                make_text_block(
                    f"list_{outcome.metrics.list_item_count}",
                    "list_item",
                    block_idx,
                    list_match.group(3).strip(),
                )
            )
            outcome.metrics.list_item_count += 1
            block_idx += 1
            continue
        if not line.strip():
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    if code_lines:
        outcome.blocks.append(
            make_text_block(
                f"code_{outcome.metrics.code_block_count}",
                "code_block",
                block_idx,
                "\n".join(code_lines),
            )
        )
        outcome.metrics.code_block_count += 1
    return outcome
