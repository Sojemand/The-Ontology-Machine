"""Pure helpers for mail page context, metadata, and block rebasing."""
from __future__ import annotations

import copy
import hashlib
import re

from ..models import BlockPosition, BlockType, DataBlock, ValueType


def stable_id(prefix: str, *parts: object) -> str:
    payload = "::".join(str(part or "") for part in parts)
    return f"{prefix}_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:10]}"


def body_render_lines(message: dict[str, object]) -> list[str]:
    headers = dict(message.get("headers", {}) or {})
    lines = [f"{label}: {headers[key]}" for label, key in (("From", "from"), ("To", "to"), ("Cc", "cc"), ("Subject", "subject"), ("Date", "date")) if headers.get(key)]
    attachment_names = [str(item.get("name", "")).strip() for item in message.get("attachments", []) if str(item.get("name", "")).strip()]
    if attachment_names:
        lines.append(f"Attachments: {', '.join(attachment_names)}")
    body_text = str(message.get("body_text", "") or "").strip() or "[Kein sichtbarer Nachrichtentext]"
    if lines:
        lines.append("")
    lines.extend(body_text.splitlines() or [body_text])
    return lines


def body_blocks(message: dict[str, object], *, page_number: int, block_prefix: str) -> list[DataBlock]:
    blocks: list[DataBlock] = []
    paragraph_index = 0
    headers = dict(message.get("headers", {}) or {})
    for label, key in (("From", "from"), ("To", "to"), ("Cc", "cc"), ("Subject", "subject"), ("Date", "date")):
        value = str(headers.get(key, "") or "").strip()
        if not value:
            continue
        blocks.append(DataBlock(id=f"{block_prefix}{key}_{paragraph_index:04d}", type=BlockType.EMAIL_FIELD, position=BlockPosition(page=page_number, paragraph_index=paragraph_index), value=f"{label}: {value}", value_type=ValueType.TEXT))
        paragraph_index += 1
    attachment_names = [str(item.get("name", "")).strip() for item in message.get("attachments", []) if str(item.get("name", "")).strip()]
    if attachment_names:
        blocks.append(DataBlock(id=f"{block_prefix}attachments_{paragraph_index:04d}", type=BlockType.METADATA, position=BlockPosition(page=page_number, paragraph_index=paragraph_index), value=f"Attachments: {', '.join(attachment_names)}", value_type=ValueType.TEXT))
        paragraph_index += 1
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", str(message.get("body_text", "") or "").strip()) if part.strip()] or ["[Kein sichtbarer Nachrichtentext]"]
    for body_index, paragraph in enumerate(paragraphs, start=paragraph_index):
        blocks.append(DataBlock(id=f"{block_prefix}body_{body_index:04d}", type=BlockType.PARAGRAPH, position=BlockPosition(page=page_number, paragraph_index=body_index), value=paragraph, value_type=ValueType.TEXT))
    return blocks


def summary_metadata(manifest: dict[str, object], logical_messages: list[dict[str, object]]) -> dict[str, object]:
    first_message = logical_messages[0] if logical_messages else {}
    headers = dict(first_message.get("headers", {}) or {})
    attachments = [attachment for message in logical_messages for attachment in message.get("attachments", []) if isinstance(attachment, dict)]
    attachment_names = [str(attachment.get("name", "")).strip() for attachment in attachments if str(attachment.get("name", "")).strip()]
    return {
        "email_from": headers.get("from", ""),
        "email_to": headers.get("to", ""),
        "email_cc": headers.get("cc", ""),
        "email_subject": headers.get("subject", ""),
        "email_date": headers.get("date", ""),
        "attachment_count": len(attachments),
        "attachment_names": ", ".join(attachment_names) if attachment_names else "",
        "body_length": sum(len(str(message.get("body_text", "") or "")) for message in logical_messages),
        "email_body_preview": str(first_message.get("body_text", "") or "")[:240].replace("\n", " ").strip(),
        "has_html_body": any(bool(message.get("html_body_path")) for message in manifest.get("messages", []) if isinstance(message, dict)),
        "message_count": len(logical_messages),
    }


def rebase_blocks(blocks: list[DataBlock], *, page_offset: int, block_prefix: str) -> list[DataBlock]:
    rebased: list[DataBlock] = []
    for index, block in enumerate(blocks):
        position = copy.deepcopy(block.position)
        position.page = max(1, int(position.page or 1) + page_offset)
        rebased.append(
            DataBlock(
                id=f"{block_prefix}{block.id or f'b{index:04d}'}",
                type=block.type,
                position=position,
                value=block.value,
                value_type=block.value_type,
                formatting=copy.deepcopy(block.formatting),
                page_span=copy.deepcopy(block.page_span),
                origin=copy.deepcopy(block.origin),
                confidence=block.confidence,
            )
        )
    return rebased
