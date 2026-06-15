"""RFC822 / mbox bundle extraction helpers."""
from __future__ import annotations

import email
import email.policy
from email.message import Message
import mailbox
from pathlib import Path
from typing import Any

from .common import (
    attachment_target_path,
    create_bundle_root,
    ensure_text,
    parse_sender,
    safe_filename,
    save_manifest,
    strip_html_to_text,
    write_bytes,
    write_text,
)

_MIME_EXTENSION_MAP = {
    "application/pdf": ".pdf",
    "application/rtf": ".rtf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-outlook": ".msg",
    "message/rfc822": ".eml",
    "text/plain": ".txt",
    "text/html": ".html",
    "application/zip": ".zip",
}


def extract_rfc822_bundle(input_path: str | Path) -> tuple[Path, dict[str, Any]]:
    source = Path(input_path)
    bundle_root = create_bundle_root("fom-rfc822-")
    ext = source.suffix.lower()
    messages: list[dict[str, Any]] = []
    if ext == ".mbox":
        mbox = mailbox.mbox(str(source))
        try:
            for index, item in enumerate(mbox, start=1):
                raw = item.as_bytes(unixfrom=False)
                message = email.message_from_bytes(raw, policy=email.policy.default)
                messages.append(_extract_message(bundle_root, message, native_part_key=f"msg_{index:04d}"))
        finally:
            mbox.close()
    else:
        if ext == ".emlx":
            message = email.message_from_bytes(_read_emlx_bytes(source), policy=email.policy.default)
        else:
            with source.open("rb") as handle:
                message = email.message_from_binary_file(handle, policy=email.policy.default)
        messages.append(_extract_message(bundle_root, message, native_part_key="msg_0001"))
    manifest = {
        "bundle_version": 1,
        "container_kind": "rfc822",
        "source_name": source.name,
        "messages": messages,
    }
    save_manifest(bundle_root, manifest)
    return bundle_root, manifest


def _read_emlx_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    first_line, _, remainder = payload.partition(b"\n")
    try:
        length = int(first_line.strip() or b"0")
    except ValueError:
        return payload
    if length <= 0 or len(remainder) < length:
        return remainder or payload
    return remainder[:length]


def _extract_message(bundle_root: Path, message: Message, *, native_part_key: str) -> dict[str, Any]:
    message_dir = bundle_root / "messages" / native_part_key
    attachments_dir = message_dir / "attachments"
    plain_bodies: list[str] = []
    html_bodies: list[str] = []
    attachments: list[dict[str, Any]] = []
    if message.is_multipart():
        attachment_index = 0
        for part in message.walk():
            if part.is_multipart():
                continue
            content_type = ensure_text(part.get_content_type()).strip().lower()
            disposition = ensure_text(part.get_content_disposition() or "").strip().lower()
            is_body_part = content_type in {"text/plain", "text/html"} and disposition != "attachment"
            if is_body_part and content_type == "text/plain":
                plain_bodies.append(_part_text(part))
                continue
            if is_body_part and content_type == "text/html":
                html_bodies.append(_part_text(part))
                continue
            attachment_index += 1
            attachments.append(
                _save_part_attachment(
                    bundle_root=bundle_root,
                    attachments_dir=attachments_dir,
                    part=part,
                    native_part_key=f"att_{attachment_index:04d}",
                    fallback_name=f"attachment_{attachment_index:04d}",
                )
            )
    else:
        content_type = ensure_text(message.get_content_type()).strip().lower()
        if content_type == "text/html":
            html_bodies.append(_part_text(message))
        else:
            plain_bodies.append(_part_text(message))

    plain_text = "\n\n".join(part.strip() for part in plain_bodies if part.strip()).strip()
    html_text = "\n\n".join(part.strip() for part in html_bodies if part.strip()).strip()
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

    from_header = ensure_text(message.get("From", "")).strip()
    sender_display, sender_address = parse_sender(from_header)
    return {
        "native_part_key": native_part_key,
        "headers": {
            "from": from_header,
            "to": ensure_text(message.get("To", "")).strip(),
            "cc": ensure_text(message.get("Cc", "")).strip(),
            "subject": ensure_text(message.get("Subject", "")).strip(),
            "date": ensure_text(message.get("Date", "")).strip(),
        },
        "sender_display": sender_display,
        "sender_address": sender_address,
        "plain_body_path": plain_path,
        "html_body_path": html_path,
        "body_text": plain_text,
        "attachments": attachments,
    }


def _part_text(part: Message) -> str:
    try:
        return ensure_text(part.get_content())
    except Exception:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ensure_text(part.get_payload())
        charset = ensure_text(part.get_content_charset() or "").strip()
        if charset:
            try:
                return payload.decode(charset)
            except UnicodeDecodeError:
                pass
        return ensure_text(payload)


def _save_part_attachment(
    *,
    bundle_root: Path,
    attachments_dir: Path,
    part: Message,
    native_part_key: str,
    fallback_name: str,
) -> dict[str, Any]:
    content_type = ensure_text(part.get_content_type()).strip().lower()
    content_id = ensure_text(part.get("Content-ID", "")).strip("<> ")
    disposition = ensure_text(part.get_content_disposition() or "").strip().lower()
    default_ext = _MIME_EXTENSION_MAP.get(content_type, "")
    filename = safe_filename(part.get_filename() or "", fallback_name, default_ext=default_ext)
    target_path = attachment_target_path(attachments_dir, native_part_key, filename)
    payload = part.get_payload(decode=True)
    if payload is None and content_type == "message/rfc822":
        nested = part.get_payload()
        if isinstance(nested, list) and nested:
            payload = nested[0].as_bytes(policy=email.policy.default)
    write_bytes(target_path, payload or b"")
    return {
        "native_part_key": native_part_key,
        "name": filename,
        "path": target_path.resolve().relative_to(bundle_root.resolve()).as_posix(),
        "content_type": content_type,
        "content_id": content_id,
        "is_inline": disposition == "inline" or bool(content_id),
    }
