from __future__ import annotations

from ingestion_layer_vision.models import FileFormat, FileTooLargeError, IngestorError, InputFileNotFoundError, OutputFilters, PluginError, UnsupportedFormatError, human_size


class TestFileFormat:
    def test_from_ext_variants(self):
        assert FileFormat.from_ext(".pdf") == FileFormat.PDF
        assert FileFormat.from_ext(".jpg") == FileFormat.IMAGE
        assert FileFormat.from_ext(".png") == FileFormat.IMAGE
        assert FileFormat.from_ext(".txt") == FileFormat.TEXT
        assert FileFormat.from_ext(".md") == FileFormat.TEXT
        assert FileFormat.from_ext(".xyz") == FileFormat.UNKNOWN
        assert FileFormat.from_ext(".xlsx") == FileFormat.UNKNOWN
        assert FileFormat.from_ext(".PDF") == FileFormat.PDF
        assert FileFormat.from_ext(".TXT") == FileFormat.TEXT


class TestHumanSize:
    def test_human_size_variants(self):
        assert human_size(500) == "500 B"
        assert "KB" in human_size(45231)
        assert "MB" in human_size(2_500_000)
        assert human_size(0) == "0 B"


class TestExceptions:
    def test_exception_hierarchy_and_messages(self):
        assert issubclass(IngestorError, Exception)
        assert issubclass(PluginError, IngestorError)
        assert issubclass(UnsupportedFormatError, IngestorError)
        assert issubclass(FileTooLargeError, IngestorError)
        assert issubclass(InputFileNotFoundError, IngestorError)
        err = PluginError("xlsx-openpyxl", "Timeout")
        assert "xlsx-openpyxl" in str(err)
        assert "Timeout" in str(err)
        assert err.plugin_name == "xlsx-openpyxl"


class TestOutputFilters:
    def test_negative_batch_size_is_normalized_to_zero(self):
        assert OutputFilters(batch_size=-5).batch_size == 0
