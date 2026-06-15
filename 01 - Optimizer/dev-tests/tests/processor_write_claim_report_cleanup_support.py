from __future__ import annotations

import json
import uuid

import pytest

from processor_write_edge_env import make_processor


class TestClaimChildOutputDir:
    def test_claim_child_output_dir_all_32_retries_exhausted(self, tmp_path, monkeypatch):
        proc = make_processor(tmp_path)
        monkeypatch.setattr(proc, "_try_claim_output_dir", lambda self_or_path, *a: None)

        with pytest.raises(RuntimeError, match="Kein kollisionsfreies"):
            proc._claim_child_output_dir(tmp_path / "base")


class TestWriteReport:
    def test_write_report_excludes_transient_fields(self, tmp_path):
        proc = make_processor(tmp_path)
        proc._report.current_file = "test.pdf"
        proc._report.current_plugin = "plugin"

        proc._write_report()

        report_path = proc._output_dir / "ingestion_report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "current_file" not in data
        assert "current_plugin" not in data


class TestCleanup:
    def test_cleanup_removes_raw_outputs(self, tmp_path):
        proc = make_processor(tmp_path)
        raw1 = proc._extracts_dir / "extract1.raw.json"
        raw2 = proc._extracts_dir / "extract2.raw.json"
        raw1.write_text("{}")
        raw2.write_text("{}")

        proc._cleanup_generated_output(
            output_dir=proc._output_dir,
            raw_paths=[raw1, raw2],
            image_paths=[],
            asset_dirs=[],
            ingest_id=str(uuid.uuid4()),
        )

        assert not raw1.exists()
        assert not raw2.exists()

    def test_cleanup_handles_already_deleted_files(self, tmp_path):
        proc = make_processor(tmp_path)
        proc._cleanup_generated_output(
            output_dir=proc._output_dir,
            raw_paths=[proc._extracts_dir / "ghost.raw.json"],
            image_paths=[],
            asset_dirs=[],
            ingest_id=str(uuid.uuid4()),
        )
