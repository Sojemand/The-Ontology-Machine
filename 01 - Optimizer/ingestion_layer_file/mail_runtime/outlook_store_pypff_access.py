"""Reflection helpers for optional pypff objects."""
from __future__ import annotations

from typing import Any

from .common import ensure_text


def safe_get(target: Any, name: str) -> Any:
    try:
        return getattr(target, name)
    except Exception:
        return None


def first_available_value(target: Any, *names: str) -> Any:
    for name in names:
        value = safe_get(target, name)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
            except Exception:
                continue
        if value not in (None, ""):
            return value
    return None


def safe_call_zero_arg(target: Any, name: str) -> Any:
    candidate = safe_get(target, name)
    if not callable(candidate):
        return None
    try:
        return candidate()
    except Exception:
        return None


def safe_call_index(target: Any, name: str, index: int) -> Any:
    candidate = safe_get(target, name)
    if not callable(candidate):
        return None
    for effective_index in (index, index + 1):
        try:
            value = candidate(effective_index)
        except Exception:
            continue
        if value is not None:
            return value
    return None


def iter_pypff_sub_messages(folder: Any) -> list[Any]:
    direct = safe_get(folder, "sub_messages")
    if isinstance(direct, (list, tuple)):
        return [item for item in direct if item is not None]
    count = safe_int(
        first_available_value(folder, "number_of_sub_messages", "get_number_of_sub_messages", "number_of_messages")
    )
    if count is None:
        return []
    messages: list[Any] = []
    for index in range(count):
        value = safe_call_index(folder, "get_sub_message", index) or safe_call_index(folder, "get_message", index)
        if value is not None:
            messages.append(value)
    return messages


def iter_pypff_sub_folders(folder: Any) -> list[Any]:
    direct = safe_get(folder, "sub_folders")
    if isinstance(direct, (list, tuple)):
        return [item for item in direct if item is not None]
    count = safe_int(
        first_available_value(folder, "number_of_sub_folders", "get_number_of_sub_folders", "number_of_folders")
    )
    if count is None:
        return []
    children: list[Any] = []
    for index in range(count):
        value = safe_call_index(folder, "get_sub_folder", index) or safe_call_index(folder, "get_folder", index)
        if value is not None:
            children.append(value)
    return children


def iter_pypff_attachments(message: Any) -> list[Any]:
    direct = safe_get(message, "attachments")
    if isinstance(direct, (list, tuple)):
        return [item for item in direct if item is not None]
    count = safe_int(first_available_value(message, "number_of_attachments", "get_number_of_attachments"))
    if count is None:
        return []
    attachments: list[Any] = []
    for index in range(count):
        value = safe_call_index(message, "get_attachment", index)
        if value is not None:
            attachments.append(value)
    return attachments


def attachment_payload(attachment: Any) -> bytes | None:
    direct = safe_get(attachment, "data")
    if isinstance(direct, (bytes, bytearray)):
        return bytes(direct)
    payload = safe_call_zero_arg(attachment, "get_data")
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    reader = safe_get(attachment, "read_buffer")
    if callable(reader):
        size = safe_int(first_available_value(attachment, "size", "get_size", "data_size", "get_data_size"))
        for candidate_size in (size, None):
            try:
                chunk = reader() if candidate_size is None else reader(candidate_size)
            except TypeError:
                continue
            except Exception:
                return None
            if isinstance(chunk, (bytes, bytearray)):
                return bytes(chunk)
    return None


def attachment_default_ext(attachment: Any) -> str:
    content_type = ensure_text(
        first_available_value(attachment, "mime_type", "get_mime_type", "content_type")
    ).strip().lower()
    if content_type == "message/rfc822":
        return ".eml"
    return ""


def pypff_root_folder(container: Any) -> Any:
    direct = safe_get(container, "root_folder")
    if direct is not None:
        return direct
    return safe_call_zero_arg(container, "get_root_folder")


def require_value(value: Any, message: str) -> Any:
    if value is None:
        raise RuntimeError(message)
    return value


def normalize_datetime(value: Any) -> str:
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:
            pass
    return ensure_text(value).strip().replace("/", "-")


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
