from __future__ import annotations

from ingestion_layer_vision.input_catalog import InputCatalog


class TestInputCatalogPagination:
    def test_iter_entries_first_page(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        entries = catalog.iter_entries(offset=0, limit=3)
        assert len(entries) == 3
        assert entries[0].filename == "doc0.pdf"

    def test_iter_entries_offset(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        entries = catalog.iter_entries(offset=5, limit=50)
        assert len(entries) == 2
        assert entries[0].filename == "file3.xlsx"

    def test_iter_entries_beyond(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        assert catalog.iter_entries(offset=100, limit=50) == []
