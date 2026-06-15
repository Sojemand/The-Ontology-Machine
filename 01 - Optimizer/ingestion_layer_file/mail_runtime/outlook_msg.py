"""Outlook .msg / .oft bundle extraction helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import (
    attachment_target_path,
    create_bundle_root,
    ensure_text,
    parse_sender,
    safe_filename,
    save_external_file,
    save_manifest,
    strip_html_to_text,
    write_text,
)


def extract_msg_bundle(input_path: str | Path) -> tuple[Path, dict[str, Any]]:
    import extract_msg

    source = Path(input_path)
    bundle_root = create_bundle_root("fom-msg-")
    with extract_msg.Message(str(source)) as message:
        entry = _extract_message(bundle_root, message, native_part_key="msg_0001")
    manifest = {
        "bundle_version": 1,
        "container_kind": "outlook_msg",
        "source_name": source.name,
        "messages": [entry],
    }
    save_manifest(bundle_root, manifest)
    return bundle_root, manifest


def _extract_message(bundle_root: Path, message: Any, *, native_part_key: str) -> dict[str, Any]:
    message_dir = bundle_root / "messages" / native_part_key
    plain_text = ensure_text(getattr(message, "body", "")).strip()
    html_text = ensure_text(getattr(message, "htmlBody", "")).strip()
    if not plain_text and html_text:
        plain_text = strip_html_to_text(html_text)

    plain_path = ""
    html_path = ""
    if plain_text:
        plain_file = message_dir / "body.txt"
        write_text(plain_file, plain_text)
        plain_path = plain_file.resolve().relative_to(bundle_root.resolve()).as_posix()
    if html_text:
        html_file = message_dir / "body.html"
        write_text(html_file, html_text)
        html_path = html_file.resolve().relative_to(bundle_root.resolve()).as_posix()

    from_header = ensure_text(getattr(message, "sender", "")).strip()
    sender_display, sender_address = parse_sender(from_header)
    attachments = _save_attachments(bundle_root, message_dir / "attachments", list(getattr(message, "attachments", []) or []))
    return {
        "native_part_key": native_part_key,
        "headers": {
            "from": from_header,
            "to": ensure_text(getattr(message, "to", "")).strip(),
            "cc": ensure_text(getattr(message, "cc", "")).strip(),
            "subject": ensure_text(getattr(message, "subject", "")).strip(),
            "date": ensure_text(getattr(message, "date", "")).strip(),
        },
        "sender_display": sender_display,
        "sender_address": sender_address,
        "plain_body_path": plain_path,
        "html_body_path": html_path,
        "body_text": plain_text,
        "attachments": attachments,
    }


def _save_attachments(bundle_root: Path, attachments_dir: Path, attachments: list[Any]) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for index, attachment in enumerate(attachments, start=1):
        native_part_key = f"att_{index:04d}"
        original_name = (
            ensure_text(getattr(attachment, "longFilename", "")).strip()
            or ensure_text(getattr(attachment, "shortFilename", "")).strip()
            or ensure_text(getattr(attachment, "displayName", "")).strip()
            or f"attachment_{index:04d}"
        )
        filename = safe_filename(original_name, f"attachment_{index:04d}", default_ext=ensure_text(getattr(attachment, "extension", "")).strip())
        target_path = attachment_target_path(attachments_dir, native_part_key, filename)
        saved_file = save_external_file(
            target_path,
            lambda staged_path: attachment.save(customPath=str(staged_path.parent), customFilename=staged_path.name),
        )
        if not saved_file:
            continue
        content_id = ensure_text(getattr(attachment, "cid", "")).strip("<> ")
        saved.append(
            {
                "native_part_key": native_part_key,
                "name": filename,
                "path": target_path.resolve().relative_to(bundle_root.resolve()).as_posix(),
                "content_type": ensure_text(getattr(attachment, "mimetype", "")).strip(),
                "content_id": content_id,
                "is_inline": bool(getattr(attachment, "hidden", False)) or bool(content_id),
            }
        )
    return saved
