from __future__ import annotations

from orchestrator.model_catalog import CatalogRefreshResult, GroupRefreshResult, ModelCatalogGroup, ModelCatalogState
from orchestrator.ui import model_catalog_actions

from .model_catalog_ui_support import _app


def test_finish_model_catalog_refresh_ignores_stale_results() -> None:
    app = _app()
    stale = CatalogRefreshResult(
        state=ModelCatalogState(
            llm_shared=ModelCatalogGroup(models=("gpt-stale",), refreshed_at="now", source="shared_llm_api_key")
        ),
        group_results={"llm_shared": GroupRefreshResult("llm_shared", "updated", "stale")},
    )

    model_catalog_actions.finish_model_catalog_refresh(app, 1, result=stale)

    assert app._model_catalog_state.llm_shared.models == ()
    assert app._model_catalog_refreshing is True


def test_finish_model_catalog_refresh_keeps_invalid_selection_visible() -> None:
    app = _app()
    result = CatalogRefreshResult(
        state=ModelCatalogState(
            llm_shared=ModelCatalogGroup(models=("gpt-5.4", "gpt-5.4-mini"), refreshed_at="now", source="shared_llm_api_key"),
            optimizer_ocr=ModelCatalogGroup(models=("gpt-5.4",), refreshed_at="now", source="optimizer_ocr_api_key"),
            embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="now", source="embeddings_api_key"),
        ),
        group_results={
            "llm_shared": GroupRefreshResult("llm_shared", "updated", "llm ok"),
            "optimizer_ocr": GroupRefreshResult("optimizer_ocr", "updated", "ocr ok"),
            "embeddings": GroupRefreshResult("embeddings", "updated", "embed ok"),
        },
    )
    app._runtime_settings_widgets["interpreter"]["model"].set("gpt-legacy")

    model_catalog_actions.finish_model_catalog_refresh(app, 2, result=result)

    assert app._runtime_settings_widgets["interpreter"]["model"].get() == "gpt-legacy"
    assert app._runtime_settings_widgets["interpreter"]["model_status"].cget("text") == "No longer in the current provider catalog"


def test_refresh_notice_deduplicates_repeated_messages() -> None:
    notice = model_catalog_actions._refresh_notice(
        {
            "llm_shared": GroupRefreshResult("llm_shared", "cached", "OpenAI OAuth active; using cache/seed."),
            "optimizer_ocr": GroupRefreshResult("optimizer_ocr", "cached", "OpenAI OAuth active; using cache/seed."),
            "embeddings": GroupRefreshResult("embeddings", "updated", "3 models imported."),
        }
    )

    assert notice == "OpenAI OAuth active; using cache/seed. | 3 models imported."
