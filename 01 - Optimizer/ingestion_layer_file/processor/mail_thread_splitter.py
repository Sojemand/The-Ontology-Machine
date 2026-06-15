"""Logical message splitting for mail containers."""
from __future__ import annotations

from email.utils import parseaddr
import re
from typing import Any

from ..models import FileFormat

_RE_ORIGINAL_MESSAGE = re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.IGNORECASE)
_RE_ON_WROTE = re.compile(r"^\s*On .+?\b(?P<sender>.+?) wrote:\s*$", re.IGNORECASE)
_RE_AM_SCHRIEB = re.compile(r"^\s*Am .+?\bschrieb\s+(?P<sender>.+?):\s*$", re.IGNORECASE)
_RE_HEADER_FROM = re.compile(r"^\s*(From|Von):\s*(?P<value>.+)\s*$", re.IGNORECASE)
_RE_HEADER_DATE = re.compile(r"^\s*(Sent|Gesendet|Date):\s*(?P<value>.+)\s*$", re.IGNORECASE)
_RE_HEADER_TO = re.compile(r"^\s*(To|An):\s*(?P<value>.+)\s*$", re.IGNORECASE)
_RE_HEADER_CC = re.compile(r"^\s*Cc:\s*(?P<value>.+)\s*$", re.IGNORECASE)
_RE_HEADER_SUBJECT = re.compile(r"^\s*(Subject|Betreff):\s*(?P<value>.+)\s*$", re.IGNORECASE)


def logical_messages(manifest: dict[str, Any], fmt: str) -> list[dict[str, Any]]:
    messages = [message for message in manifest.get("messages", []) if isinstance(message, dict)]
    if fmt in {FileFormat.MBOX, FileFormat.PST, FileFormat.OST}:
        return [_container_message(message) for message in messages]
    logical: list[dict[str, Any]] = []
    for message in messages:
        logical.extend(split_thread_message(message))
    return logical


def split_thread_message(message: dict[str, Any]) -> list[dict[str, Any]]:
    body_text = normalized_body_text(message)
    native_root = str(message.get("native_part_key", "msg_0001"))
    base_headers = dict(message.get("headers", {}) or {})
    sender_display = str(message.get("sender_display", "") or "") or str(base_headers.get("from", "") or "")
    sender_address = str(message.get("sender_address", "") or "")
    attachments = visible_attachments(message)
    lines = body_text.splitlines()
    markers = _quote_markers(lines)
    if not markers:
        return [_logical_segment(native_root, 1, base_headers, sender_display, sender_address, body_text, "exact", attachments)]
    logical = [_logical_segment(native_root, 1, base_headers, sender_display, sender_address, "\n".join(lines[: markers[0]["index"]]).strip(), "exact", attachments)]
    next_segment = 2
    for marker_index, marker in enumerate(markers):
        start = marker["index"]
        end = markers[marker_index + 1]["index"] if marker_index + 1 < len(markers) else len(lines)
        segment = _marker_segment(marker, lines[start:end])
        if not segment["exact"]:
            logical.append(_logical_segment(native_root, next_segment, dict(segment.get("headers", {}) or {}), str(segment.get("sender_display", "") or ""), str(segment.get("sender_address", "") or ""), "\n".join(lines[start:]).strip(), "merged_unsure", []))
            break
        logical.append(_logical_segment(native_root, next_segment, dict(segment.get("headers", {}) or {}), str(segment.get("sender_display", "") or ""), str(segment.get("sender_address", "") or ""), str(segment.get("body_text", "") or ""), "exact", []))
        next_segment += 1
    return logical


def parse_sender(value: str) -> tuple[str, str]:
    display, address = parseaddr(str(value or "").strip())
    normalized_address = address.strip()
    normalized_display = display.strip() or normalized_address or str(value or "").strip()
    return normalized_display, normalized_address


def visible_attachments(message: dict[str, Any]) -> list[dict[str, Any]]:
    return [attachment for attachment in message.get("attachments", []) if isinstance(attachment, dict) and not bool(attachment.get("is_inline"))]


def normalized_body_text(message: dict[str, Any]) -> str:
    return str(message.get("body_text", "") or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _container_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "native_part_key": str(message.get("native_part_key", "msg_0001")),
        "headers": dict(message.get("headers", {}) or {}),
        "sender_display": str(message.get("sender_display", "") or ""),
        "sender_address": str(message.get("sender_address", "") or ""),
        "body_text": normalized_body_text(message),
        "split_mode": "exact",
        "attachments": visible_attachments(message),
    }


def _logical_segment(native_root: str, index: int, headers: dict[str, str], sender_display: str, sender_address: str, body_text: str, split_mode: str, attachments: list[dict[str, Any]]) -> dict[str, Any]:
    return {"native_part_key": f"{native_root}__seg_{index:04d}", "headers": headers, "sender_display": sender_display, "sender_address": sender_address, "body_text": body_text, "split_mode": split_mode, "attachments": attachments}


def _quote_markers(lines: list[str]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if index == 0 or not line.strip():
            continue
        stripped = line.strip()
        if _RE_ORIGINAL_MESSAGE.match(stripped):
            markers.append({"index": index, "type": "original_message", "line": line})
            continue
        on_match = _RE_ON_WROTE.match(stripped)
        if on_match:
            markers.append({"index": index, "type": "on_wrote", "line": line, "sender": on_match.group("sender").strip()})
            continue
        am_match = _RE_AM_SCHRIEB.match(stripped)
        if am_match:
            markers.append({"index": index, "type": "am_schrieb", "line": line, "sender": am_match.group("sender").strip()})
            continue
        if _looks_like_header_block(lines, index) and not _RE_ORIGINAL_MESSAGE.match(lines[index - 1].strip()):
            markers.append({"index": index, "type": "header_block", "line": line})
    return markers


def _marker_segment(marker: dict[str, Any], lines: list[str]) -> dict[str, Any]:
    kind = str(marker.get("type", ""))
    if kind in {"on_wrote", "am_schrieb"}:
        sender_display, sender_address = parse_sender(str(marker.get("sender", "")))
        return {"exact": bool(sender_display), "headers": {"from": sender_display or str(marker.get("sender", "")).strip()}, "sender_display": sender_display, "sender_address": sender_address, "body_text": "\n".join(lines[1:]).strip()}
    header_lines = lines[1:] if kind == "original_message" else lines
    if kind not in {"original_message", "header_block"}:
        return {"exact": False, "headers": {}, "sender_display": "", "sender_address": "", "body_text": "\n".join(lines).strip()}
    headers, body_lines, ok = _header_block(header_lines)
    sender_display, sender_address = parse_sender(str(headers.get("from", "")))
    return {"exact": ok and bool(sender_display), "headers": headers, "sender_display": sender_display, "sender_address": sender_address, "body_text": "\n".join(body_lines).strip()}


def _header_block(lines: list[str]) -> tuple[dict[str, str], list[str], bool]:
    headers = {"from": "", "to": "", "cc": "", "subject": "", "date": ""}
    body_start = 0
    saw_header = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            body_start = index + 1
            if saw_header:
                break
            continue
        matched = False
        for pattern, key in ((_RE_HEADER_FROM, "from"), (_RE_HEADER_TO, "to"), (_RE_HEADER_CC, "cc"), (_RE_HEADER_SUBJECT, "subject"), (_RE_HEADER_DATE, "date")):
            match = pattern.match(stripped)
            if match:
                headers[key] = match.group("value").strip()
                saw_header = True
                matched = True
                break
        if saw_header and not matched:
            body_start = index
            break
    return headers, lines[body_start:], bool(headers.get("from"))


def _looks_like_header_block(lines: list[str], index: int) -> bool:
    if not _RE_HEADER_FROM.match(lines[index].strip()):
        return False
    window = lines[index : index + 8]
    return any(_RE_HEADER_DATE.match(line.strip()) for line in window) and any(_RE_HEADER_TO.match(line.strip()) for line in window)
