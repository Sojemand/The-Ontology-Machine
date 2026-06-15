from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import policy_store
from orchestrator.integrations.corpus_semantics import semantic_status
from orchestrator.integrations.types import ModuleContractError

from tests.test_integrations_workflow import _runtime_spec


def test_semantic_status_prefers_direct_provider(tmp_path: Path) -> None:
    class Modules:
        def semantic_status(self, corpus_db_path: Path | None) -> dict[str, object]:
            return {
                "corpus_db_path": str(corpus_db_path) if corpus_db_path is not None else "",
                "published_release_path": "C:/release/default.json",
                "runtime_truth_source": "uninitialized",
            }

    detail = semantic_status(Modules(), corpus_db_path=tmp_path / "selected.db")

    assert detail["published_release_path"] == "C:/release/default.json"
    assert detail["corpus_db_path"] == str(tmp_path / "selected.db")


def test_semantic_status_invokes_contract_and_unwraps_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type(
        "Modules",
        (),
        {
            "_runtime_specs": {
                "corpus_builder": _runtime_spec(tmp_path, "corpus_builder"),
            }
        },
    )()
    captured: list[tuple[str, dict[str, object], int]] = []

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured.append((spec.key, payload, timeout))
        return {
            "status": "ok",
            "detail": {
                "published_release_path": "C:/release/default.json",
                "runtime_truth_source": "db_snapshot",
            },
        }

    monkeypatch.setattr("orchestrator.integrations.corpus_semantics.adapter.invoke_contract", fake_invoke)

    detail = semantic_status(modules, corpus_db_path=tmp_path / "selected.db")

    assert captured == [
        (
            "corpus_builder",
            {
                "action": "semantic_status",
                "corpus_db_path": str(tmp_path / "selected.db"),
            },
            policy_store.projection_catalog_timeout_seconds(),
        )
    ]
    assert detail["runtime_truth_source"] == "db_snapshot"


def test_semantic_status_rejects_error_payload() -> None:
    class Modules:
        def semantic_status(self, corpus_db_path: Path | None) -> dict[str, object]:
            del corpus_db_path
            return {"status": "error", "reason": "blocked"}

    with pytest.raises(ModuleContractError, match="blocked"):
        semantic_status(Modules(), corpus_db_path=Path("C:/tmp/corpus.db"))
