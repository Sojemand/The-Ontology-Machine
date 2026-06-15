from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.integrations.projection_catalog import load_normalizer_projection_catalog
from orchestrator.integrations.types import ModuleContractError
from tests.test_integrations_workflow import _runtime_spec


def test_load_normalizer_projection_catalog_returns_contract_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type("Modules", (), {"_runtime_specs": {"normalizer": _runtime_spec(tmp_path, "normalizer")}})()

    monkeypatch.setattr(
        "orchestrator.integrations.projection_catalog.adapter.invoke_contract",
        lambda *_args, **_kwargs: {
            "status": "OK",
            "projection_catalog": {
                "catalog_version": "sha256:test",
                "master_taxonomy_version": "2026-03-28.v5",
                "master_taxonomy_release_id": "sha256:master-line",
                "runtime_locale": "en",
                "projections": [],
            },
        },
    )

    result = load_normalizer_projection_catalog(modules)

    assert result == {
        "catalog_version": "sha256:test",
        "master_taxonomy_version": "2026-03-28.v5",
        "master_taxonomy_release_id": "sha256:master-line",
        "runtime_locale": "en",
        "projections": [],
    }


def test_load_normalizer_projection_catalog_rejects_invalid_contract_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type("Modules", (), {"_runtime_specs": {"normalizer": _runtime_spec(tmp_path, "normalizer")}})()
    monkeypatch.setattr(
        "orchestrator.integrations.projection_catalog.adapter.invoke_contract",
        lambda *_args, **_kwargs: {"status": "OK", "projection_catalog": {"projections": []}},
    )

    with pytest.raises(ModuleContractError, match="catalog_version"):
        load_normalizer_projection_catalog(modules)


def test_load_normalizer_projection_catalog_skips_non_runtime_module_sets() -> None:
    assert load_normalizer_projection_catalog(object()) is None
