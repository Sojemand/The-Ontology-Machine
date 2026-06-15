from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import policy_store
from orchestrator.integrations.release_activation import activation_preflight
from orchestrator.integrations.types import ModuleContractError

from tests.test_integrations_workflow import _runtime_spec


def test_activation_preflight_prefers_direct_provider(tmp_path: Path) -> None:
    class Modules:
        def activation_preflight(self, release_path: Path, corpus_db_path: Path) -> dict[str, object]:
            return {
                "release_path": str(release_path),
                "corpus_db_path": str(corpus_db_path),
                "requires_confirmation": False,
                "no_op": True,
            }

    detail = activation_preflight(
        Modules(),
        release_path=tmp_path / "release.json",
        corpus_db_path=tmp_path / "corpus.db",
    )

    assert detail["no_op"] is True
    assert detail["release_path"] == str(tmp_path / "release.json")


def test_activation_preflight_forwards_contract_payload_and_unwraps_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
                "requires_confirmation": True,
                "no_op": False,
                "next_snapshot": {"snapshot_id": "sha256:new"},
            },
        }

    monkeypatch.setattr("orchestrator.integrations.release_activation.adapter.invoke_contract", fake_invoke)

    detail = activation_preflight(
        modules,
        release_path=tmp_path / "release.json",
        corpus_db_path=tmp_path / "corpus.db",
    )

    assert captured == [
        (
            "corpus_builder",
            {
                "action": "activation_preflight",
                "release_path": str(tmp_path / "release.json"),
                "corpus_db_path": str(tmp_path / "corpus.db"),
            },
            policy_store.projection_catalog_timeout_seconds(),
        )
    ]
    assert detail["next_snapshot"]["snapshot_id"] == "sha256:new"


def test_activation_preflight_rejects_error_payload() -> None:
    class Modules:
        def activation_preflight(self, release_path: Path, corpus_db_path: Path) -> dict[str, object]:
            del release_path, corpus_db_path
            return {"status": "error", "reason": "blocked"}

    with pytest.raises(ModuleContractError, match="blocked"):
        activation_preflight(
            Modules(),
            release_path=Path("C:/tmp/release.json"),
            corpus_db_path=Path("C:/tmp/corpus.db"),
        )
