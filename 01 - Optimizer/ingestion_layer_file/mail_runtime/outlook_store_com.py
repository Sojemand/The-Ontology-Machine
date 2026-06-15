"""Outlook COM backend for PST/OST bundle extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import (
    attachment_target_path,
    ensure_text,
    parse_sender,
    safe_filename,
    save_external_file,
    strip_html_to_text,
    write_text,
)
from .outlook_store_com_support import iter_collection, normalize_datetime, normalize_store_path, safe_get

_OL_MAIL_CLASS = 43


def _selftest_outlook_com_backend() -> tuple[bool, str]:
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            if namespace is None:
                return False, "Outlook COM antwortet nicht auf MAPI."
            return True, "OK (win32com + Outlook MAPI)"
        finally:
            pythoncom.CoUninitialize()
    except Exception as exc:
        return False, f"Outlook COM nicht verfuegbar: {exc}"


def _extract_via_outlook_com(bundle_root: Path, source: Path) -> list[dict[str, Any]]:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    namespace = None
    root_folder = None
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        existing_paths = {normalize_store_path(safe_get(store, "FilePath")) for store in namespace.Stores}
        try:
            namespace.AddStoreEx(str(source.resolve()), 3)
        except Exception:
            namespace.AddStore(str(source.resolve()))
        store = _match_store(namespace, source, existing_paths)
        root_folder = store.GetRootFolder()
        messages: list[dict[str, Any]] = []
        folder_counter = [0]
        _walk_folder(bundle_root, root_folder, messages, folder_counter, path_prefix=())
        return messages
    finally:
        if namespace is not None and root_folder is not None:
            try:
                namespace.RemoveStore(root_folder)
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _walk_folder(
    bundle_root: Path,
    folder: Any,
    messages: list[dict[str, Any]],
    folder_counter: list[int],
    *,
    path_prefix: tuple[int, ...],
) -> None:
    folder_counter[0] += 1
    folder_index = folder_counter[0]
    items = iter_collection(safe_get(folder, "Items"))
    message_index = 0
    for item in items:
        if int(safe_get(item, "Class") or 0) != _OL_MAIL_CLASS:
            continue
        message_index += 1
        native_part_key = "msg_" + "_".join(f"{part:04d}" for part in (*path_prefix, folder_index, message_index))
        messages.append(_extract_mail_item(bundle_root, item, native_part_key=native_part_key))
    folders = iter_collection(safe_get(folder, "Folders"))
    for child_index, child in enumerate(folders, start=1):
        _walk_folder(bundle_root, child, messages, folder_counter, path_prefix=(*path_prefix, folder_index, child_index))


def _extract_mail_item(bundle_root: Path, item: Any, *, native_part_key: str) -> dict[str, Any]:
    message_dir = bundle_root / "messages" / native_part_key
    html_text = ensure_text(safe_get(item, "HTMLBody")).strip()
    plain_text = ensure_text(safe_get(item, "Body")).strip()
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

    from_header = ensure_text(safe_get(item, "SenderName")).strip()
    sender_display, sender_address = parse_sender(from_header or ensure_text(safe_get(item, "SenderEmailAddress")).strip())
    attachments = _extract_outlook_attachments(bundle_root, message_dir / "attachments", safe_get(item, "Attachments"))
    return {
        "native_part_key": native_part_key,
        "headers": {
            "from": from_header or sender_display,
            "to": ensure_text(safe_get(item, "To")).strip(),
            "cc": ensure_text(safe_get(item, "CC")).strip(),
            "subject": ensure_text(safe_get(item, "Subject")).strip(),
            "date": normalize_datetime(safe_get(item, "ReceivedTime") or safe_get(item, "SentOn") or safe_get(item, "CreationTime")),
        },
        "sender_display": sender_display,
        "sender_address": sender_address,
        "plain_body_path": plain_path,
        "html_body_path": html_path,
        "body_text": plain_text,
        "attachments": attachments,
    }


def _extract_outlook_attachments(bundle_root: Path, attachments_dir: Path, attachments: Any) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for index, attachment in enumerate(iter_collection(attachments), start=1):
        native_part_key = f"att_{index:04d}"
        original_name = ensure_text(safe_get(attachment, "FileName")).strip() or f"attachment_{index:04d}"
        filename = safe_filename(original_name, f"attachment_{index:04d}")
        target_path = attachment_target_path(attachments_dir, native_part_key, filename)
        saved_file = save_external_file(target_path, lambda staged_path: attachment.SaveAsFile(str(staged_path)))
        if not saved_file:
            continue
        saved.append(
            {
                "native_part_key": native_part_key,
                "name": filename,
                "path": target_path.resolve().relative_to(bundle_root.resolve()).as_posix(),
                "content_type": "",
                "content_id": "",
                "is_inline": False,
            }
        )
    return saved


def _match_store(namespace: Any, source: Path, existing_paths: set[str]) -> Any:
    normalized_source = normalize_store_path(str(source.resolve()))
    stores = list(iter_collection(namespace.Stores))
    for store in stores:
        store_path = normalize_store_path(safe_get(store, "FilePath"))
        if store_path == normalized_source:
            return store
    for store in reversed(stores):
        store_path = normalize_store_path(safe_get(store, "FilePath"))
        if store_path and store_path not in existing_paths:
            return store
    raise RuntimeError(f"Outlook-Store konnte nicht geoeffnet werden: {source}")
