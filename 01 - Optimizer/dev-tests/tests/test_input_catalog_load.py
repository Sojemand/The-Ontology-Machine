from __future__ import annotations

from ingestion_layer_vision.input_catalog import InputCatalog


class TestInputCatalogLoad:
    def test_load_empty_input(self, tmp_path):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        state_dir.mkdir()
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert catalog.refresh()
        assert catalog.total_count == 0

    def test_load_summary(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        assert catalog.refresh()
        assert catalog.total_count == 7
        assert catalog.summary[".xlsx"] == 5
        assert catalog.summary[".pdf"] == 2
        assert catalog.total_size > 0

    def test_load_nonexistent_and_loaded_property(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        missing = InputCatalog(tmp_path / "nope", state_dir=state_dir)
        assert not missing.refresh()
        assert missing.total_count == 0
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        assert not catalog.loaded
        catalog.refresh()
        assert catalog.loaded


class TestInputCatalogState:
    def test_path_setter_resets(self, sample_input_dir, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(sample_input_dir, state_dir=state_dir)
        catalog.refresh()
        catalog.path = tmp_path / "other"
        assert not catalog.loaded
        assert catalog.total_count == 0
