from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import policy_store
from orchestrator.integrations.runtime_semantic_assets import build_runtime_semantic_assets, read_active_semantic_release
from orchestrator.integrations.types import ModuleContractError
from tests.test_integrations_workflow import _runtime_spec

from .integrations_runtime_semantic_assets_support import _release_detail, _release_payload, _runtime_assets


def test_read_active_semantic_release_prefers_direct_reader(tmp_path: Path) -> None:
    class Modules:
        def read_active_semantic_release(self, corpus_db_path: Path) -> dict[str, object]:
            return _release_detail(corpus_db_path)

    detail = read_active_semantic_release(Modules(), corpus_db_path=tmp_path / "corpus.db")

    assert detail["release_id"] == "semantic_release.default"
    assert detail["fingerprint"] == "sha256:semantic-default"
    assert detail["release"]["master_taxonomy_release_id"] == "sha256:master-line"
    assert detail["release"]["runtime_locale"] == "en"


def test_runtime_semantic_helpers_forward_expected_contract_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type(
        "Modules",
        (),
        {
            "_runtime_specs": {
                "corpus_builder": _runtime_spec(tmp_path, "corpus_builder"),
                "normalizer": _runtime_spec(tmp_path, "normalizer"),
            }
        },
    )()
    captured: list[tuple[str, dict[str, object], int]] = []

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured.append((spec.key, payload, timeout))
        if spec.key == "corpus_builder":
            return {"status": "ok", "detail": _release_detail(Path(str(payload["corpus_db_path"])))}
        return {"status": "OK", "runtime_semantic_assets": _runtime_assets(_release_payload())}

    monkeypatch.setattr("orchestrator.integrations.runtime_semantic_assets.adapter.invoke_contract", fake_invoke)

    detail = read_active_semantic_release(modules, corpus_db_path=tmp_path / "corpus.db")
    assets = build_runtime_semantic_assets(modules, release=detail["release"])

    assert captured == [
        (
            "corpus_builder",
            {"action": "read_active_semantic_release", "corpus_db_path": str(tmp_path / "corpus.db")},
            policy_store.projection_catalog_timeout_seconds(),
        ),
        (
            "normalizer",
            {"action": "build_runtime_semantic_assets", "release": _release_payload()},
            policy_store.projection_catalog_timeout_seconds(),
        ),
    ]
    assert assets["projection_catalog"]["release_fingerprint"] == "sha256:semantic-default"
    assert assets["projection_catalog"]["master_taxonomy_release_id"] == "sha256:master-line"
    assert assets["projection_catalog"]["runtime_locale"] == "en"
    assert assets["master_taxonomy_release_id"] == "sha256:master-line"
    assert assets["runtime_locale"] == "en"


def test_read_active_semantic_release_rejects_missing_release() -> None:
    class Modules:
        def read_active_semantic_release(self, corpus_db_path: Path) -> dict[str, object]:
            del corpus_db_path
            return {"status": {}}

    with pytest.raises(ModuleContractError, match="release_detail.release"):
        read_active_semantic_release(Modules(), corpus_db_path=Path("C:/tmp/corpus.db"))
