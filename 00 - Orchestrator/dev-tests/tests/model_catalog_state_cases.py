from __future__ import annotations

from orchestrator.model_catalog import (
    ModelCatalogGroup,
    ModelCatalogState,
    effective_model_catalog_state,
    load_model_catalog_state,
    save_model_catalog_state,
)
from orchestrator.models import RuntimeSettingsState


def test_model_catalog_state_roundtrip(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(models=("gpt-5.4",), refreshed_at="2026-03-30T15:00:00Z", source="shared_llm_api_key"),
        optimizer_ocr=ModelCatalogGroup(models=("gpt-5.4",), refreshed_at="2026-03-30T15:00:00Z", source="optimizer_ocr_api_key"),
        embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="2026-03-30T15:00:00Z", source="embeddings_api_key"),
    )

    save_model_catalog_state(state_dir, state)
    loaded = load_model_catalog_state(state_dir)

    assert loaded.to_dict() == state.to_dict()


def test_effective_model_catalog_state_seeds_from_runtime_settings() -> None:
    state = effective_model_catalog_state(
        ModelCatalogState(),
        RuntimeSettingsState.from_dict(
            {
                "schema_version": 1,
                "interpreter": {"model": "gpt-5.4", "max_output_tokens": 8000},
                "normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
                "corpus_builder_embeddings": {"model": "text-embedding-3-small"},
            }
        ),
    )

    assert state.llm_shared.models == (
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.5-pro",
        "gpt-5.5",
        "gpt-5.5-mini",
        "gpt-5.5-nano",
        "gpt-5.4-pro",
        "gpt-5.4-nano",
        "gpt-5.2-pro",
        "gpt-5.2",
        "gpt-5.2-mini",
        "gpt-5.2-nano",
        "gpt-5.1",
        "gpt-5.1-mini",
        "gpt-5.1-nano",
        "gpt-5-pro",
        "gpt-5",
        "gpt-5-chat-latest",
        "gpt-5-mini",
        "gpt-5-nano",
    )
    assert state.optimizer_ocr.models == (
        "gpt-5.4",
        "gpt-5.5-pro",
        "gpt-5.5",
        "gpt-5.5-mini",
        "gpt-5.5-nano",
        "gpt-5.4-pro",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5.2-pro",
        "gpt-5.2",
        "gpt-5.2-mini",
        "gpt-5.2-nano",
        "gpt-5.1",
        "gpt-5.1-mini",
        "gpt-5.1-nano",
        "gpt-5-pro",
        "gpt-5",
        "gpt-5-chat-latest",
        "gpt-5-mini",
        "gpt-5-nano",
    )
    assert state.embeddings.models == ("text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002")
    assert state.llm_shared.source == "runtime_settings_seed"
