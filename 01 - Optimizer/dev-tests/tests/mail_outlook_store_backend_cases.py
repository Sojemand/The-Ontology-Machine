from __future__ import annotations

from pathlib import Path

from ingestion_layer_file.mail_runtime import outlook_store

from mail_outlook_store_fakes import _FakeAttachment, _FakeFolder, _FakeMessage, _FakePypffFile, _FakePypffModule


def test_extract_outlook_store_bundle_prefers_pypff_backend(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "archive.pst"
    source.write_text("stub", encoding="utf-8")
    fake_file = _FakePypffFile(
        _FakeFolder(messages=[_FakeMessage([_FakeAttachment("note.txt", b"hello world")])])
    )
    monkeypatch.setitem(__import__("sys").modules, "pypff", _FakePypffModule(fake_file))
    monkeypatch.setattr(
        outlook_store,
        "_extract_via_outlook_com",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("COM fallback must stay unused")),
    )

    bundle_root, manifest = outlook_store.extract_outlook_store_bundle(source)

    assert manifest["backend"] == "pypff"
    assert manifest["messages"][0]["headers"]["subject"] == "Quarterly archive"
    assert fake_file.opened_path == str(source)
    assert fake_file.closed is True
    attachment_path = bundle_root / manifest["messages"][0]["attachments"][0]["path"]
    assert attachment_path.read_bytes() == b"hello world"


def test_extract_outlook_store_bundle_falls_back_to_com_when_pypff_is_missing(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "archive.ost"
    source.write_text("stub", encoding="utf-8")
    monkeypatch.delitem(__import__("sys").modules, "pypff", raising=False)
    monkeypatch.setattr(
        outlook_store,
        "_extract_via_outlook_com",
        lambda _bundle_root, _source: [
            {
                "native_part_key": "msg_0001",
                "headers": {"subject": "COM message"},
                "attachments": [],
                "body_text": "",
            }
        ],
    )

    _bundle_root, manifest = outlook_store.extract_outlook_store_bundle(source)

    assert manifest["backend"] == "outlook_com"
    assert manifest["messages"][0]["headers"]["subject"] == "COM message"


def test_selftest_outlook_store_backend_prefers_pypff(monkeypatch) -> None:
    monkeypatch.setattr(outlook_store, "_import_pypff", lambda: object())
    monkeypatch.setattr(
        outlook_store,
        "_selftest_outlook_com_backend",
        lambda: (_ for _ in ()).throw(AssertionError("COM fallback must stay unused")),
    )

    ok, detail = outlook_store.selftest_outlook_store_backend()

    assert ok is True
    assert detail == "OK (pypff)"
