from __future__ import annotations

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import OutputFilters


class TestInputCatalogFilter:
    def test_filter_by_format(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        entries = list(catalog.iter_filtered(OutputFilters(format=".pdf")))
        assert len(entries) == 2
        assert all(entry.extension == ".pdf" for entry in entries)

    def test_filter_by_size_and_batch(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        assert len(list(catalog.iter_filtered(OutputFilters(max_size_mb=1)))) == 7
        assert len(list(catalog.iter_filtered(OutputFilters(batch_size=3)))) == 3

    def test_count_after_filter_and_no_match(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        assert catalog.count_after_filter(OutputFilters(format=".xlsx")) == 5
        assert list(catalog.iter_filtered(OutputFilters(format=".docx"))) == []
