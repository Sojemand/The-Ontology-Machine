"""pypff-backed Outlook store message extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .common import attachment_target_path, ensure_text, parse_sender, safe_filename, strip_html_to_text, write_bytes, write_text
from .outlook_store_pypff_access import (
    attachment_default_ext,
    attachment_payload,
    first_available_value,
    iter_pypff_attachments,
    iter_pypff_sub_folders,
    iter_pypff_sub_messages,
    normalize_datetime,
    pypff_root_folder,
    require_value,
    safe_call_zero_arg,
)


def extract_via_pypff(
    bundle_root: Path,
    source: Path,
    *,
    import_pypff: Callable[[], Any],
) -> list[dict[str, Any]]:
    pypff = import_pypff()
    container = pypff.file()
    try:
        container.open(str(source))
        root_folder = require_value(
            pypff_root_folder(container),
            f"pypff lieferte keinen Root-Folder fuer {source.name}",
        )
        messages: list[dict[str, Any]] = []
        folder_counter = [0]
        _walk_pypff_folder(bundle_root, root_folder, messages, folder_counter, path_prefix=())
        return messages
    finally:
        safe_call_zero_arg(container, "close")


def _walk_pypff_folder(
    bundle_root: Path,
    folder: Any,
    messages: list[dict[str, Any]],
    folder_counter: list[int],
    *,
    path_prefix: tuple[int, ...],
) -> None:
    folder_counter[0] += 1
    folder_index = folder_counter[0]
    for message_index, message in enumerate(iter_pypff_sub_messages(folder), start=1):
        native_part_key = "msg_" + "_".join(
            f"{part:04d}" for part in (*path_prefix, folder_index, message_index)
        )
        messages.append(_extract_pypff_message(bundle_root, message, native_part_key=native_part_key))
    for child_index, child in enumerate(iter_pypff_sub_folders(folder), start=1):
        _walk_pypff_folder(
            bundle_root,
            child,
            messages,
            folder_counter,
            path_prefix=(*path_prefix, folder_index, child_index),
        )


def _extract_pypff_message(bundle_root: Path, message: Any, *, native_part_key: str) -> dict[str, Any]:
    message_dir = bundle_root / "messages" / native_part_key
    html_text = ensure_text(first_available_value(message, "html_body", "get_html_body")).strip()
    plain_text = ensure_text(
        first_available_value(message, "plain_text_body", "get_plain_text_body", "body", "get_body")
    ).strip()
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

    sender_name = ensure_text(first_available_value(message, "sender_name", "get_sender_name")).strip()
    sender_email = ensure_text(
        first_available_value(message, "sender_email_address", "get_sender_email_address")
    ).strip()
    from_header = sender_name if not sender_email else f"{sender_name} <{sender_email}>".strip()
    sender_display, sender_address = parse_sender(from_header or sender_email)
    return {
        "native_part_key": native_part_key,
        "headers": {
            "from": from_header or sender_display,
            "to": ensure_text(first_available_value(message, "display_to", "get_display_to", "received_by_name")).strip(),
            "cc": ensure_text(first_available_value(message, "display_cc", "get_display_cc")).strip(),
            "subject": ensure_text(first_available_value(message, "subject", "get_subject")).strip(),
            "date": normalize_datetime(
                first_available_value(
                    message,
                    "delivery_time",
                    "get_delivery_time",
                    "client_submit_time",
                    "get_client_submit_time",
                    "creation_time",
                    "get_creation_time",
                )
            ),
        },
        "sender_display": sender_display,
        "sender_address": sender_address,
        "plain_body_path": plain_path,
        "html_body_path": html_path,
        "body_text": plain_text,
        "attachments": _extract_pypff_attachments(bundle_root, message_dir / "attachments", message),
    }


def _extract_pypff_attachments(bundle_root: Path, attachments_dir: Path, message: Any) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for index, attachment in enumerate(iter_pypff_attachments(message), start=1):
        payload = attachment_payload(attachment)
        if payload is None:
            continue
        native_part_key = f"att_{index:04d}"
        original_name = ensure_text(
            first_available_value(
                attachment,
                "name",
                "get_name",
                "long_filename",
                "get_long_filename",
                "filename",
                "get_filename",
                "display_name",
                "get_display_name",
            )
        ).strip()
        filename = safe_filename(
            original_name,
            f"attachment_{index:04d}",
            default_ext=attachment_default_ext(attachment),
        )
        target_path = attachment_target_path(attachments_dir, native_part_key, filename)
        write_bytes(target_path, payload)
        saved.append(
            {
                "native_part_key": native_part_key,
                "name": filename,
                "path": target_path.resolve().relative_to(bundle_root.resolve()).as_posix(),
                "content_type": ensure_text(
                    first_available_value(attachment, "mime_type", "get_mime_type", "content_type")
                ).strip(),
                "content_id": ensure_text(first_available_value(attachment, "content_id", "get_content_id")).strip(),
                "is_inline": False,
            }
        )
    return saved
