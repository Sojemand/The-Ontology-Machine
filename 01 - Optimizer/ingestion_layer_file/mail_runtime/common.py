"""Common helpers for mail-container extraction bundles."""
from __future__ import annotations

from email.utils import parseaddr
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable

from ..models import atomic_bytes_write, atomic_file_copy, atomic_json_write, atomic_text_write

_INLINE_TEXT_LIMIT = 4000
_PREVIEW_BODY_LIMIT = 240
_MAX_SAFE_FILENAME_LENGTH = 160
_WINDOWS_PATH_BUDGET = 259
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_BREAK_RE = re.compile(r"</?(?:br|p|div|li|tr|h[1-6])\b[^>]*>", re.IGNORECASE)
_HTML_SCRIPT_RE = re.compile(r"<(script|style)\b.*?>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"[ \t]+")


def create_bundle_root(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16-le", "cp1252", "latin-1"):
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace")
    return str(value)


def strip_html_to_text(value: str) -> str:
    text = ensure_text(value)
    if not text.strip():
        return ""
    text = _HTML_SCRIPT_RE.sub(" ", text)
    text = _HTML_BREAK_RE.sub("\n", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def parse_sender(value: str) -> tuple[str, str]:
    display, address = parseaddr(ensure_text(value).strip())
    normalized_address = address.strip()
    normalized_display = display.strip()
    if not normalized_display and normalized_address:
        normalized_display = normalized_address
    if not normalized_display:
        normalized_display = ensure_text(value).strip()
    return normalized_display, normalized_address


def safe_filename(value: str, fallback: str, *, default_ext: str = "", max_length: int = _MAX_SAFE_FILENAME_LENGTH) -> str:
    candidate = ensure_text(value).strip()
    if not candidate:
        candidate = fallback
    candidate = candidate.replace("\\", "_").replace("/", "_").replace(":", "_")
    candidate = _FILENAME_SAFE_RE.sub("_", candidate).strip("._-")
    if not candidate:
        candidate = fallback
    suffix = Path(candidate).suffix
    if default_ext and not suffix:
        candidate = f"{candidate}{default_ext}"
    return _truncate_filename(candidate, max_length=max_length)


def attachment_target_path(attachments_dir: Path, native_part_key: str, filename: str) -> Path:
    safe_key = safe_filename(native_part_key, "att", max_length=64)
    safe_name = safe_filename(filename, "attachment")
    preferred_name = f"{safe_key}_{safe_name}"
    if _within_path_budget(attachments_dir, preferred_name):
        return attachments_dir / preferred_name

    max_name_length = max(1, _WINDOWS_PATH_BUDGET - len(str(attachments_dir)) - 1)
    suffix = Path(safe_name).suffix
    stem = safe_name[: -len(suffix)] if suffix else safe_name
    digest = hashlib.sha1(f"{safe_key}|{safe_name}".encode("utf-8")).hexdigest()[:8]
    reserved = len(safe_key) + len(digest) + len(suffix) + 2
    keep = max(1, max_name_length - reserved)
    candidate = f"{safe_key}_{(stem[:keep].rstrip('._-') or 'attachment')}.{digest}{suffix}"
    if _within_path_budget(attachments_dir, candidate):
        return attachments_dir / candidate

    compact_key = _truncate_filename(safe_key, max_length=max(3, min(len(safe_key), max_name_length - len(digest) - len(suffix) - 2)))
    reserved = len(compact_key) + len(digest) + len(suffix) + 2
    keep = max(0, max_name_length - reserved)
    if keep:
        candidate = f"{compact_key}_{(stem[:keep].rstrip('._-') or 'attachment')}.{digest}{suffix}"
    else:
        candidate = f"{compact_key}.{digest}{suffix}"
    return attachments_dir / _truncate_filename(candidate, max_length=max_name_length)


def write_text(path: Path, content: str) -> None:
    atomic_text_write(path, ensure_text(content))


def write_bytes(path: Path, content: bytes) -> None:
    atomic_bytes_write(path, content)


def save_external_file(path: Path, saver: Callable[[Path], None]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix if path.suffix else ".bin"
    fd = -1
    staged_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=".ms.", suffix=suffix, dir=str(path.parent))
        staged_path = Path(tmp_name)
        os.close(fd)
        fd = -1
        staged_path.unlink(missing_ok=True)
        saver(staged_path)
        if not staged_path.is_file():
            return False
        atomic_file_copy(staged_path, path)
        return True
    finally:
        if fd != -1:
            os.close(fd)
        if staged_path is not None:
            try:
                staged_path.unlink(missing_ok=True)
            except OSError:
                pass


def save_manifest(bundle_root: Path, manifest: dict[str, Any]) -> Path:
    manifest_path = bundle_root / "manifest.json"
    atomic_json_write(manifest_path, manifest)
    return manifest_path


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    messages = [item for item in manifest.get("messages", []) if isinstance(item, dict)]
    first_message = messages[0] if messages else {}
    headers = first_message.get("headers", {}) if isinstance(first_message.get("headers"), dict) else {}
    attachment_names: list[str] = []
    attachment_count = 0
    has_html = False
    total_body_length = 0
    for message in messages:
        attachment_entries = [item for item in message.get("attachments", []) if isinstance(item, dict) and not bool(item.get("is_inline"))]
        attachment_count += len(attachment_entries)
        attachment_names.extend(str(item.get("name", "")).strip() for item in attachment_entries if str(item.get("name", "")).strip())
        if message.get("html_body_path"):
            has_html = True
        total_body_length += len(ensure_text(message.get("body_text")))
    preview = ensure_text(first_message.get("body_text"))[:_PREVIEW_BODY_LIMIT].replace("\n", " ").strip()
    return {
        "email_from": headers.get("from", ""),
        "email_to": headers.get("to", ""),
        "email_cc": headers.get("cc", ""),
        "email_subject": headers.get("subject", ""),
        "email_date": headers.get("date", ""),
        "attachment_count": attachment_count,
        "attachment_names": ", ".join(attachment_names) if attachment_names else "",
        "body_length": total_body_length,
        "email_body_preview": preview,
        "has_html_body": has_html,
        "message_count": len(messages),
    }


def build_preview_blocks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    messages = [item for item in manifest.get("messages", []) if isinstance(item, dict)]
    if not messages:
        return []
    first_message = messages[0]
    headers = first_message.get("headers", {}) if isinstance(first_message.get("headers"), dict) else {}
    blocks: list[dict[str, Any]] = []
    paragraph_index = 0
    for key in ("from", "to", "cc", "subject", "date"):
        value = ensure_text(headers.get(key)).strip()
        if not value:
            continue
        blocks.append(
            _block(
                block_id=f"mail_header_{key}",
                block_type="email_field",
                value=f"{key.title()}: {value}",
                paragraph_index=paragraph_index,
            )
        )
        paragraph_index += 1
    body = ensure_text(first_message.get("body_text"))[:_INLINE_TEXT_LIMIT]
    for index, paragraph in enumerate(_paragraphs(body), start=paragraph_index):
        blocks.append(
            _block(
                block_id=f"mail_body_{index}",
                block_type="paragraph",
                value=paragraph,
                paragraph_index=index,
            )
        )
    return blocks


def _block(*, block_id: str, block_type: str, value: str, paragraph_index: int) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": block_type,
        "position": {
            "sheet": None,
            "row": None,
            "col": None,
            "col_letter": None,
            "page": None,
            "paragraph_index": paragraph_index,
            "table_index": None,
        },
        "value": value,
        "value_type": "text",
        "formatting": None,
        "confidence": None,
    }


def _paragraphs(text: str) -> list[str]:
    payload = ensure_text(text).strip()
    if not payload:
        return []
    return [part.strip() for part in re.split(r"\n\s*\n", payload) if part.strip()]


def _truncate_filename(candidate: str, *, max_length: int) -> str:
    if len(candidate) <= max_length:
        return candidate
    suffix = Path(candidate).suffix
    if len(suffix) >= max_length:
        suffix = ""
    stem = candidate[: -len(suffix)] if suffix else candidate
    keep = max(1, max_length - len(suffix))
    return f"{stem[:keep].rstrip('._-') or 'attachment'}{suffix}"


def _within_path_budget(parent: Path, name: str) -> bool:
    return len(str(parent / name)) <= _WINDOWS_PATH_BUDGET
