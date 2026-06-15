from __future__ import annotations

import json
import uuid

from ingestion_layer_vision.input_catalog import InputCatalog
from input_catalog_support import write_completed_raw


class TestNormalizeHash:
    def test_normalize_hash_variants(self):
        assert InputCatalog._normalize_hash_value("SHA256:AABB" + "cc" * 30).startswith("sha256:aabb")
        assert InputCatalog._normalize_hash_value("  sha256:" + "ab" * 32 + "  ") == "sha256:" + "ab" * 32
        assert InputCatalog._normalize_hash_value("sha256:not-hex-at-all-nope!") is None
        assert InputCatalog._normalize_hash_value("sha256:abcd") is None
        assert InputCatalog._normalize_hash_value("aa" * 32) == "sha256:" + "aa" * 32
        assert InputCatalog._normalize_hash_value("") is None
        assert InputCatalog._normalize_hash_value("   ") is None


class TestIsValidUuid:
    def test_uuid_validation_variants(self):
        assert InputCatalog._is_valid_uuid_text("") is False
        assert InputCatalog._is_valid_uuid_text("../../etc/shadow") is False
        assert InputCatalog._is_valid_uuid_text(str(uuid.uuid4())) is True
        assert InputCatalog._is_valid_uuid_text("  " + str(uuid.uuid4()) + "  ") is True
        assert InputCatalog._is_valid_uuid_text("not-a-uuid-at-all") is False


class TestCompletedOutputHash:
    def test_completed_output_hash_variants(self, tmp_path):
        output_dir = tmp_path / "output"
        content_hash = "sha256:" + "aa" * 32
        write_completed_raw(output_dir, "test", content_hash, ingest_id="not-a-uuid")
        catalog = InputCatalog(output_dir=output_dir)
        assert catalog._completed_output_hash(output_dir / "raw_extracts" / "test.raw.json") is None
        ingest_id = str(uuid.uuid4())
        raw_dir = output_dir / "raw_extracts"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_file = raw_dir / "test2.raw.json"
        raw_file.write_text(json.dumps({"schema_version": "optimizer_raw_v2", "source": {"content_hash": content_hash, "ingest_id": ingest_id}}), encoding="utf-8")
        assert catalog._completed_output_hash(raw_file) == content_hash

