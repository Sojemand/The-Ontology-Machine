from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class _FakeAttachment:
    def __init__(self, name: str, payload: bytes, content_type: str = "text/plain") -> None:
        self.name = name
        self.size = len(payload)
        self.mime_type = content_type
        self._payload = payload

    def read_buffer(self, size: int) -> bytes:
        return self._payload[:size]


class _FakeMsgAttachment:
    longFilename = "note.txt"
    shortFilename = ""
    displayName = ""
    extension = ".txt"
    cid = ""
    mimetype = "text/plain"
    hidden = False

    def save(self, *, customPath: str, customFilename: str) -> None:
        Path(customPath, customFilename).write_bytes(b"new-msg")


class _FakeComAttachment:
    FileName = "note.txt"

    def SaveAsFile(self, path: str) -> None:
        Path(path).write_bytes(b"new-com")


class _FakeComAttachments:
    Count = 1

    def Item(self, index: int):
        if index != 1:
            raise IndexError(index)
        return _FakeComAttachment()


class _FakeMessage:
    def __init__(self, attachments: list[_FakeAttachment]) -> None:
        self.subject = "Quarterly archive"
        self.sender_name = "Alice Example"
        self.sender_email_address = "alice@example.com"
        self.display_to = "Bob Example"
        self.display_cc = "Carol Example"
        self.delivery_time = datetime(2026, 4, 18, 12, 34, tzinfo=timezone.utc)
        self.plain_text_body = "Body from pypff"
        self.number_of_attachments = len(attachments)
        self._attachments = attachments

    def get_attachment(self, index: int):
        return self._attachments[index]


class _FakeFolder:
    def __init__(self, messages: list[_FakeMessage], sub_folders: list["_FakeFolder"] | None = None) -> None:
        self.number_of_sub_messages = len(messages)
        self.number_of_sub_folders = len(sub_folders or [])
        self._messages = messages
        self._sub_folders = sub_folders or []

    def get_sub_message(self, index: int):
        return self._messages[index]

    def get_sub_folder(self, index: int):
        return self._sub_folders[index]


class _FakePypffFile:
    def __init__(self, root_folder: _FakeFolder) -> None:
        self._root_folder = root_folder
        self.opened_path = ""
        self.closed = False

    def open(self, path: str) -> None:
        self.opened_path = path

    def get_root_folder(self):
        return self._root_folder

    def close(self) -> None:
        self.closed = True


class _FakePypffModule:
    def __init__(self, file_handle: _FakePypffFile) -> None:
        self._file_handle = file_handle

    def file(self) -> _FakePypffFile:
        return self._file_handle
