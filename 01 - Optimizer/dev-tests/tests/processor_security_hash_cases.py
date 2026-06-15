from __future__ import annotations

import hashlib

from processor_security_env import catalog_entry, make_processor


def test_content_hash_invalid_non_hex_is_recomputed(tmp_path, monkeypatch):
    proc = make_processor(tmp_path)

    input_file = tmp_path / "dummy.txt"
    input_file.write_text("hello", encoding="utf-8")
    expected_hash = f"sha256:{hashlib.sha256(b'hello').hexdigest()}"
    entry = catalog_entry(input_file, content_hash="not-a-hex-string")

    captured_hash = {}
    original_build = proc._build_extract

    def spy_build(**kwargs):
        captured_hash["value"] = kwargs.get("content_hash", "")
        return original_build(**kwargs)

    monkeypatch.setattr(proc, "_build_extract", lambda **kw: spy_build(**kw))
    monkeypatch.setattr(proc, "_write_extract", lambda *_args, **_kwargs: tmp_path / "fake_extract.raw.json")

    proc._process_file(entry)

    assert "value" in captured_hash, "content_hash should have been passed to _build_extract"
    assert captured_hash["value"] == expected_hash


def test_content_hash_already_valid_no_double_prefix(tmp_path, monkeypatch):
    proc = make_processor(tmp_path)

    input_file = tmp_path / "dummy.txt"
    input_file.write_text("hello", encoding="utf-8")
    valid_hash = f"sha256:{'aa' * 32}"
    entry = catalog_entry(input_file, content_hash=valid_hash)

    captured_hash = {}
    original_build = proc._build_extract

    def spy_build(**kwargs):
        captured_hash["value"] = kwargs.get("content_hash", "")
        return original_build(**kwargs)

    monkeypatch.setattr(proc, "_build_extract", lambda **kw: spy_build(**kw))
    monkeypatch.setattr(proc, "_write_extract", lambda *_args, **_kwargs: tmp_path / "fake_extract.raw.json")

    proc._process_file(entry)

    assert captured_hash.get("value") == valid_hash, f"Valid hash should remain unchanged, got {captured_hash.get('value')!r}"
    assert not captured_hash["value"].startswith("sha256:sha256:")


def test_content_hash_raw_hex_gets_prefix(tmp_path, monkeypatch):
    proc = make_processor(tmp_path)

    input_file = tmp_path / "dummy.txt"
    input_file.write_text("hello", encoding="utf-8")
    raw_hex = "aa" * 32
    entry = catalog_entry(input_file, content_hash=raw_hex)

    captured_hash = {}
    original_build = proc._build_extract

    def spy_build(**kwargs):
        captured_hash["value"] = kwargs.get("content_hash", "")
        return original_build(**kwargs)

    monkeypatch.setattr(proc, "_build_extract", lambda **kw: spy_build(**kw))
    monkeypatch.setattr(proc, "_write_extract", lambda *_args, **_kwargs: tmp_path / "fake_extract.raw.json")

    proc._process_file(entry)

    assert captured_hash.get("value") == f"sha256:{raw_hex}", f"Raw hex hash should get 'sha256:' prefix, got {captured_hash.get('value')!r}"


def test_archive_dir_from_malformed_hash_is_sanitized_via_recompute(tmp_path):
    proc = make_processor(tmp_path)
    input_file = tmp_path / "dummy.txt"
    input_file.write_text("hello", encoding="utf-8")

    resolved_hash = proc._resolve_content_hash(input_file, "sha256:../../../bad_path")
    hash_dir_name = proc._archive_dir_name(resolved_hash)
    expected_hash = hashlib.sha256(b"hello").hexdigest()

    assert resolved_hash == f"sha256:{expected_hash}"
    assert hash_dir_name == expected_hash[:16]
    assert "/" not in hash_dir_name
    assert "\\" not in hash_dir_name
    assert ".." not in hash_dir_name

    archive_root = tmp_path / "archive"
    archive_path = (archive_root / hash_dir_name).resolve()
    assert archive_path.relative_to(archive_root.resolve())


def test_process_file_invalid_hash_and_recompute_failure_records_error(tmp_path, monkeypatch):
    proc = make_processor(tmp_path)
    input_file = tmp_path / "dummy.txt"
    input_file.write_text("hello", encoding="utf-8")

    entry = catalog_entry(input_file, content_hash="not-a-hex-string")

    monkeypatch.setattr(proc, "_compute_hash", lambda path: "")
    called = {"build": False}
    monkeypatch.setattr(
        proc,
        "_build_extract",
        lambda **kwargs: called.__setitem__("build", True),
    )

    proc._process_file(entry)

    assert called["build"] is False
    assert proc._report.failed == 1
    assert "Hash-Berechnung fehlgeschlagen" in proc._report.errors[0]["error"]
