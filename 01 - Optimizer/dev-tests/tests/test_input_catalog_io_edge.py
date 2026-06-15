from __future__ import annotations

import json
from pathlib import Path

import pytest

from ingestion_layer_vision.input_catalog import InputCatalog, _is_within
from ingestion_layer_vision.models import atomic_json_write


class TestReadHashesFromFile:
    def test_read_hashes_non_list_non_dict_rejects(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError):
            InputCatalog._read_hashes_from_file(path)

    def test_read_hashes_invalid_entries_logged(self, tmp_path, caplog):
        valid_hash = "sha256:" + "aa" * 32
        path = tmp_path / "mixed.json"
        path.write_text(json.dumps({"hashes": [valid_hash, "invalid!", ""]}), encoding="utf-8")
        result = InputCatalog._read_hashes_from_file(path)
        assert len(result) == 1
        assert valid_hash in result
        assert "ungueltige Hash-Eintraege" in caplog.text


class TestImportExport:
    def test_import_hashes_modes(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(state_dir=state_dir)
        for i in range(3):
            catalog.mark_processed_hash(f"sha256:{('%02x' % i) * 32}")
        import_path = tmp_path / "import.json"
        new_hashes = [f"sha256:{('%02x' % (i + 10)) * 32}" for i in range(2)]
        atomic_json_write(import_path, {"version": 1, "hashes": new_hashes})
        assert catalog.import_processed_hashes(import_path, replace=True) == 2
        hash_b = f"sha256:{'bb' * 32}"
        hash_c = f"sha256:{'cc' * 32}"
        catalog.mark_processed_hash(hash_b)
        atomic_json_write(import_path, {"version": 1, "hashes": [hash_b, hash_c]})
        assert catalog.import_processed_hashes(import_path, replace=False) >= 2


class TestRefreshPermissionError:
    def test_refresh_with_permission_error_on_file(self, tmp_path, monkeypatch):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        state_dir.mkdir()
        (input_dir / "ok1.txt").write_text("a", encoding="utf-8")
        (input_dir / "ok2.txt").write_text("b", encoding="utf-8")
        bad_file = input_dir / "bad.txt"
        bad_file.write_text("c", encoding="utf-8")
        original_stat = Path.stat
        call_counts: dict[str, int] = {}

        def patched_stat(self, *args, **kwargs):
            key = str(self)
            call_counts[key] = call_counts.get(key, 0) + 1
            if self.name == "bad.txt" and call_counts[key] > 1:
                raise PermissionError("access denied")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", patched_stat)
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        catalog.refresh()
        assert catalog.total_count == 2


class TestIsWithin:
    def test_is_within_variants(self):
        assert _is_within(Path("/a/b"), Path("/a/b")) is True
        assert _is_within(Path("/a/b/c"), Path("/a/b")) is True
        assert _is_within(Path("/a/x"), Path("/a/b")) is False
