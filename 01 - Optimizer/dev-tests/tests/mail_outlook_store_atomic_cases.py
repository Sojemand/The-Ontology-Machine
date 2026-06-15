from __future__ import annotations

from pathlib import Path

import pytest

import ingestion_layer_file.models.repository as model_repository
from ingestion_layer_file.mail_runtime import common, outlook_msg, outlook_store

from mail_outlook_store_fakes import _FakeComAttachments, _FakeMsgAttachment


def test_mail_bundle_manifest_write_preserves_existing_file_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"status":"old"}', encoding="utf-8")
    monkeypatch.setattr(model_repository.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))
    monkeypatch.setattr(model_repository.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError, match="locked"):
        common.save_manifest(tmp_path, {"status": "new"})

    assert manifest_path.read_text(encoding="utf-8") == '{"status":"old"}'
    assert list(tmp_path.glob("*.tmp")) == []


def test_mail_bundle_binary_write_preserves_existing_file_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    attachment_path = tmp_path / "attachment.bin"
    attachment_path.write_bytes(b"old")
    monkeypatch.setattr(model_repository.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))
    monkeypatch.setattr(model_repository.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError, match="locked"):
        common.write_bytes(attachment_path, b"new")

    assert attachment_path.read_bytes() == b"old"
    assert list(tmp_path.glob("*.tmp")) == []


def test_safe_mail_attachment_path_stays_inside_windows_budget() -> None:
    attachments_dir = (
        Path("C:/Users/Norma/AppData/Local/Temp")
        / "file-optimizer-mail-rfc822-abcdefgh"
        / "messages"
        / "msg_0001"
        / "attachments"
    )
    filename = common.safe_filename("invoice-" + ("x" * 220) + ".pdf", "attachment")

    target = common.attachment_target_path(attachments_dir, "att_0001", filename)

    assert len(str(target)) <= 259
    assert target.suffix == ".pdf"
    assert target.name.startswith("att_0001_")
    assert len(target.name) < len(f"att_0001_{filename}")


def test_msg_attachment_save_writes_long_attachment_name_inside_windows_budget(tmp_path: Path) -> None:
    class _LongMsgAttachment(_FakeMsgAttachment):
        longFilename = "invoice-" + ("x" * 220) + ".pdf"
        extension = ".pdf"

    attachments_dir = tmp_path / "fom-msg-abcdefgh" / "messages" / "msg_0001" / "attachments"

    saved = outlook_msg._save_attachments(tmp_path, attachments_dir, [_LongMsgAttachment()])

    saved_path = tmp_path / saved[0]["path"]
    assert saved_path.is_file()
    assert saved_path.read_bytes() == b"new-msg"
    assert len(str(saved_path)) <= 259
    assert saved_path.suffix == ".pdf"
    assert [path for path in attachments_dir.iterdir() if path.is_dir()] == []


def test_msg_attachment_save_preserves_existing_file_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    attachments_dir = tmp_path / "messages" / "msg_0001" / "attachments"
    target = attachments_dir / "att_0001_note.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old")
    monkeypatch.setattr(model_repository.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))
    monkeypatch.setattr(model_repository.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError, match="locked"):
        outlook_msg._save_attachments(tmp_path, attachments_dir, [_FakeMsgAttachment()])

    assert target.read_bytes() == b"old"
    assert list(attachments_dir.glob("*.tmp")) == []
    assert [path for path in attachments_dir.iterdir() if path.is_dir()] == []


def test_com_attachment_save_preserves_existing_file_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    attachments_dir = tmp_path / "messages" / "msg_0001" / "attachments"
    target = attachments_dir / "att_0001_note.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old")
    monkeypatch.setattr(model_repository.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))
    monkeypatch.setattr(model_repository.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError, match="locked"):
        outlook_store._extract_outlook_attachments(tmp_path, attachments_dir, _FakeComAttachments())

    assert target.read_bytes() == b"old"
    assert list(attachments_dir.glob("*.tmp")) == []
    assert [path for path in attachments_dir.iterdir() if path.is_dir()] == []
