from __future__ import annotations

import pytest

from orchestrator.model_catalog import ModelCatalogGroup, ModelCatalogState
from orchestrator.state import load_runtime_settings
from orchestrator.ui import repository

from .ui_repository_support import _make_app


def _populate_runtime_widget_defaults(app) -> None:
    for section, widgets in app._runtime_settings_widgets.items():
        widgets["model"].insert(0, f"{section}-model")
        if "max_output_tokens" in widgets:
            widgets["max_output_tokens"].insert(0, "1000")
        if "timeout_seconds" in widgets:
            widgets["timeout_seconds"].insert(0, "120")


def test_save_and_restore_runtime_settings_roundtrip(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._runtime_settings_widgets["interpreter"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["interpreter"]["max_output_tokens"].insert(0, "8000")
    app._runtime_settings_widgets["normalizer"]["model"].insert(0, "gpt-5.4-mini")
    app._runtime_settings_widgets["normalizer"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["optimizer_ocr"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["timeout_seconds"].insert(0, "120")
    app._runtime_settings_widgets["corpus_builder_embeddings"]["model"].insert(0, "text-embedding-3-small")

    repository.save_runtime_settings(app)

    loaded = load_runtime_settings(app._state_dir)
    restored = _make_app(tmp_path)
    restored._runtime_settings = loaded
    repository.restore_runtime_settings(restored)

    assert repository.current_runtime_settings(restored) == loaded


def test_current_runtime_settings_rejects_invalid_token_values(tmp_path) -> None:
    app = _make_app(tmp_path)
    _populate_runtime_widget_defaults(app)
    app._runtime_settings_widgets["normalizer"]["max_output_tokens"].delete(0, "end")
    app._runtime_settings_widgets["normalizer"]["max_output_tokens"].insert(0, "zero")

    with pytest.raises(ValueError, match="Normalizer: max_output_tokens"):
        repository.current_runtime_settings(app)


def test_current_runtime_settings_rejects_models_missing_from_strict_catalog(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(models=("gpt-5.4",), refreshed_at="now", source="shared_llm_api_key"),
        embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="now", source="embeddings_api_key"),
    )
    app._runtime_settings_widgets["interpreter"]["model"].insert(0, "gpt-legacy")
    app._runtime_settings_widgets["interpreter"]["max_output_tokens"].insert(0, "8000")
    app._runtime_settings_widgets["normalizer"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["normalizer"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["optimizer_ocr"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["timeout_seconds"].insert(0, "120")
    app._runtime_settings_widgets["corpus_builder_embeddings"]["model"].insert(0, "text-embedding-3-small")

    with pytest.raises(ValueError, match="Interpreter: model 'gpt-legacy'"):
        repository.current_runtime_settings(app)


def test_current_runtime_settings_prefers_effective_catalog_when_present(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(models=("gpt-stale",), refreshed_at="old", source="shared_llm_api_key"),
        embeddings=ModelCatalogGroup(models=("text-embedding-stale",), refreshed_at="old", source="embeddings_api_key"),
    )
    app._model_catalog_effective_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(models=("gpt-5.4", "gpt-5.4-mini"), refreshed_at="now", source="shared_llm_api_key"),
        embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="now", source="embeddings_api_key"),
    )
    app._runtime_settings_widgets["interpreter"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["interpreter"]["max_output_tokens"].insert(0, "8000")
    app._runtime_settings_widgets["normalizer"]["model"].insert(0, "gpt-5.4-mini")
    app._runtime_settings_widgets["normalizer"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["model"].insert(0, "gpt-5.4")
    app._runtime_settings_widgets["optimizer_ocr"]["max_output_tokens"].insert(0, "15000")
    app._runtime_settings_widgets["optimizer_ocr"]["timeout_seconds"].insert(0, "120")
    app._runtime_settings_widgets["corpus_builder_embeddings"]["model"].insert(0, "text-embedding-3-small")

    state = repository.current_runtime_settings(app)

    assert state.interpreter.model == "gpt-5.4"
    assert state.normalizer.model == "gpt-5.4-mini"
    assert state.corpus_builder_embeddings.model == "text-embedding-3-small"
